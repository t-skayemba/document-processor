import os
import json 
import re 
import logging 
from typing import Optional, Tuple 
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from models.schemas import DocumentExtraction, DocumentType

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"

# --- PROMPT TEMPLATES -------------------------------------------------------------------------------------------------------------------

INITIAL_EXTRACTION_PROMPT = """You are a document analysis expert. Analyze the following document and extract  structured information.

Return ONLY a valid JSON object - no markdown, no backticks, no explaination. Just the raw JSON.

The JSON must follow this exact structure:
{{
    "document_type": "invoice" | "contract" | "receipt" | "legal" | "financial" | "unknown",
    "confidence_score": 0.0-1.0,
    "summary": "2-4 sentence plain English summary",
    "flags": [
        {{
            "issue": "description of the issue",
            "severity": "low" | "medium" | "high" | "critical",
            "location": "where in the doc (optional)",
            "recommendation": "what to do about it"
        }}
    ],
    "invoice_data": {{ // Include ONLY if document_type is "invoice" or "receipt"
        "invoice_number": "...",
        "vendor_name": "...",
        "vendor_address": "...",
        "client_name": "...",
        "issue_date": "YYYY-MM-DD or null",
        "due_date": "YYYY-MM-DD or null",
        "subtotal": 0.00,
        "tax_amount": 0.00,
        "total_amount": 0.00,
        "currency": "USD",
        "line_items": [{{"description": "...", "quantity": 1, "unit_price": 0.00, "total": 0.00}}],
        "payment_terms": "...",
        "bank_details": "...",
    }},
    "contract_data": {{ // Inlcude ONLY if document_type is "contract" or "legal"
        "contract_type": "...",
        "parties": ["Party A", "Party B"],
        "effective_date": "YYYY-MM-DD or null",
        "expiration_date": "YYYY-MM-DD or null",
        "jurisdiction": "...",
        "governing_law": "...",
        "key_obligations": ["obligation1", "obligation2"],
        "payment_terms": "...",
        "termination_clauses": ["clause1"],
        "auto_renewal": true/false/null,
        "penalty_clauses": ["penalty 1"],
        "confidentiality_clause": true/false/null,
        "non_compete_clause": true/false/null
    }},
    "raw_key_fields": {{ // Any other important fields not captured above
        "field_name": "value"
    }}
}}

Document to analyze:
---
{document_text}
---

FLAGS TO LOOK FOR:
- Missing required fields (no due date, no signatures, etc.)
- Unusual or one-sided terms in contracts
- Mismatched totals in invoices
- Missing legal protections
- Vague or ambiguous language
- Unusually short payment terms or excessive penalties
- Missing party information

Retuern ONLY the JSON object. No other text."""

STRICT_RETRY_PROMPT = """IMPORTANT: Your previous response contained invalid JSON. This is a retry attempt.

You MUST return ONLY a raw JSON object. Follow these rules STRICTLY:
1. Start your response with {{ and end with }}
2. No text before or after the JSON
3. No markdown code blocks (no '''json)
4. No comments inside teh JSON
5. All string values must use double quotes
6. Numeric values must not be quoted
7. Use null for missing values, not empty string or "N/A"

Analyze this document and return valid JSON:
----
{document_text}
---

Required top-level keys: document_type, confidence_score, summary, flags, raw_key_fields
The flags array can be empty [] but must be present.

START YOUR RESPONSE WITH {{ NOW:"""

# --- JSON PARSING HELPERS -------------------------------------------------------------------------------------------------------------------

def clean_and_parse_json(raw_response: str) -> dict:
    """
    Attempt to parse JSON from LLM output, handling comon formatting issues.
    LLMs sometimes wrap JSON in markdown, add preamble text, or use single quotes.
    """
    text = raw_response.strip()

    # remove markdown code fences (```json ... ``` or ``` ... ``)
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # if there is text before the first {, strip it
    first_brace = text.find("{")
    if first_brace > 0:
        text = text[first_brace:]
    
    # if there is text after the last }, strip it
    last_brace = text.rfind("}")
    if last_brace != -1 and last_brace < len(text) - 1:
        text = text[:last_brace + 1]
    
    # try parsing
    return json.loads(text)

# --- CORE EXTRACTION WITH RETRY -------------------------------------------------------------------------------------------------------------------

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(anthropic.RateLimitError),
    reraise=True
)
def call_claude(prompt: str, max_tokens: int = 4096) -> str:
    """
    Call Claude API. The @retry decorator handles rate limit errors automatically
    with exponential backoff (waits 2s, then 4s, then 8s between attempts).
    """
    message = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def extract_document_data(
    document_text: str,
    filename: str,
    extraction_method: str = "text",
    page_count: int = 0,
    word_count: int = 0
) -> Tuple[Optional[DocumentExtraction], Optional[str]]:

    max_retries = int(os.getenv("MAX_RETRIES", 3))

    safe_text = document_text.replace("{", "{{").replace("}", "}}")

    for attempt in range(1, max_retries + 1):
        logger.info(f"Extraction attempt {attempt} for '{filename}'")

        raw_response = None
        parsed = None

        # Choose prompt based on attempt number
        if attempt == 1:
            prompt = INITIAL_EXTRACTION_PROMPT.format(document_text=safe_text)
        else:
            logger.warning(f"Attempt {attempt}: using strict retry prompt.")
            prompt = STRICT_RETRY_PROMPT.format(document_text=safe_text)

        # ── Step A: Call Claude ──────────────────────────────────────────────
        try:
            raw_response = call_claude(prompt)
        except anthropic.RateLimitError:
            return None, "Rate limit exceeded after retries. Please wait and try again."
        except anthropic.AuthenticationError:
            return None, "Invalid API key. Check your ANTHROPIC_API_KEY in .env"
        except Exception as e:
            logger.error(f"Claude API call failed on attempt {attempt}: {e}")
            if attempt == max_retries:
                return None, f"LLM API call failed after {attempt} attempts: {str(e)}"
            continue

        # ── Step B: Parse JSON ───────────────────────────────────────────────
        try:
            parsed = clean_and_parse_json(raw_response)
        except (json.JSONDecodeError, NameError, KeyError, ValueError) as e:
            logger.warning(f"JSON parse failed on attempt {attempt}: {e}")
            logger.debug(f"Raw response: {raw_response[:500] if raw_response else 'None'}")
            if attempt == max_retries:
                return None, f"LLM returned invalid JSON after {attempt} attempts: {str(e)}"
            continue
        except Exception as e:
            logger.warning(f"Unexpected parse error on attempt {attempt}: {e}")
            logger.debug(f"Raw response: {raw_response[:500] if raw_response else 'None'}")
            if attempt == max_retries:
                return None, f"Failed to parse LLM response after {attempt} attempts: {str(e)}"
            continue

        # Guard: make sure we actually got a dict back
        if not isinstance(parsed, dict):
            logger.warning(
                f"Parsed result is not a dict on attempt {attempt}: "
                f"{type(parsed)}"
            )
            if attempt == max_retries:
                return None, "LLM response did not produce a valid JSON object."
            continue

        # ── Step C: Pydantic Validation ──────────────────────────────────────
        try:
            parsed["page_count"]        = page_count
            parsed["word_count"]        = word_count
            parsed["extraction_method"] = extraction_method

            extraction = DocumentExtraction(**parsed)
            logger.info(
                f"Successfully extracted data from '{filename}' "
                f"on attempt {attempt}"
            )
            return extraction, None

        except Exception as e:
            logger.warning(f"Pydantic validation failed on attempt {attempt}: {e}")
            if attempt == max_retries:
                return None, (
                    f"Extracted data failed validation after "
                    f"{attempt} attempts: {str(e)}"
                )
            continue

    return None, "Extraction failed after all retry attempts."