import logging
from typing import Tuple, Optional 
from dataclasses import dataclass, field 

from utils.file_utils import (
    validate_file,
    is_password_protected,
    is_scanned_pdf,
    extract_text_from_pdf,
    get_file_info,
    get_document_size_strategy,
    split_by_natural_boundaries
)
from agent.ocr import run_ocr
from agent.extractor import extract_document_data, call_claude
from agent.retry_queue import add_job, update_job, JobStatus
from models.schemas import DocumentExtraction, ProcessingStatus

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """Everything the UI needs to display results."""
    status: ProcessingStatus
    extraction: Optional[DocumentExtraction] = None
    error_message: Optional[str] = None
    job_id: Optional[int] = None
    file_info: Optional[dict] = None
    used_ocr: bool = False
    processing_steps: list = field(default_factory=list)

# --- Large document helper --------------------------------------------------
def process_large_document(chunks: list[str], filename: str) -> str:
    """
    Summarize each chunk individually, then combine the summaries.
    The combined summary becomes the "document text" snt to teh main
    extraction step - nothing gets dropped.
    """
    summaries = []

    for i, chunk in enumerate(chunks):
        logger.info(f"Summarizing chunk {i + 1}/{len(chunks)} of '{filename}'...")

        prompt = f""" You are summarizing section {i + 1} of {len(chunks)} of a \
        legal or financial document. Another AI will use your summary to extract \
        structured data, so preserve everything factual.

        Extract and keep ALL of the following if present:
        - Party naes, roles, and contact details
        - Dates, deadlines, notice periods, and time limits
        - Dollar amounts, payment schedules, penalties, and fees
        - Obligations, deliverables, and responsibilities
        - Key clauses: termination, liability, IP ownership, non-compete,
        confidentiality, indemnification, displute resolution
        - Any numbers, percentages, thersholds, or conditions
        - Signatures, execution dates, and govening jurisdiction

        Be thorough and factual. Do not editoialize or shorten facts.

        Document section {i + 1} of {len(chunks)}
        ---
        {chunk}
        ---

        Structured summary:"""
        try:
            summary = call_claude(prompt, max_tokens=1500)
            summaries.append(f"[SECTION] {i + 1} OR {len(chunks)}]\n{summary}")
            logger.info(f"✓ Chunk {i + 1}/{len(chunks)} summarized successfully")
        except Exception as e:
            logger.warning(
                f"Chunk {i + 1} summarization failed: {e}."
                f"Including raw chunk text as fallback."
            )
            summaries.append(
                f"[SECTION {i + 1} OF {len(chunks)} - RAW FALLBACK]\n"
                f"{chunk[:3000]}"
            )
    
    combined = "\n\n".join(summaries)
    logger.info(
        f"All {len(chunks)} chunks processed. "
        f"Combined summary: {len(combined):,} chars."
    )
    return combined

# --- Main processor --------------------------------------------------

def process_document(file_bytes: bytes, filename: str) -> ProcessingResult:
    """
    The main entry point. Takes raw file bytes, returns a ProcessingResult.

    Decision flow:
    1. Validate file (size, type, not empty, magic bytes)
    2. Check if password protected
    3. Register in retry queue
    4. Determine if scanned or text-based PDF
    5. Extract text (direct) or run OCR (scanned)
    6. Determine size strategy: single pass / chunk+summarize / reject
    7. If chunking: split -> summarize each chunk -> combine summaries
    8. Send to LLM for structured extraction + Pydantic validation
    9. Update queue with result and return
    """
    steps = []
    file_info = get_file_info(file_bytes, filename)

    def log_step(msg: str, is_error: bool = False):
        """Tracking processing steps for UI display and logging."""
        if is_error:
            logging.error(msg)
        else:
            logger.info(msg)
        steps.append({"message": msg, "is_error": is_error})
    
    def fail (error: str, job_id: int = None, used_ocr: bool = False) -> ProcessingResult:
        """Helper to build a consistent failure result."""
        log_step(error, is_error=True)
        if job_id is not None:
            update_job(job_id, JobStatus.FAILED, error=error)
        return ProcessingResult(
            status=ProcessingStatus.FAILED,
            error_message=error,
            job_id=job_id,
            used_ocr=used_ocr,
            file_info=file_info,
            processing_steps=steps
        )
    
    # --- STEP 1: File Validation --------------------------------------------------
    log_step(f"Validating file: {filename} ({file_info['size_mb']} MB)")
    is_valid, validation_error = validate_file(file_bytes, filename)

    if not is_valid:
        return fail(validation_error)
    
    log_step("✓ File validation passed")

    # --- STEP 2: Password Protection Check --------------------------------------------------
    log_step("Checking for password protection...")

    if is_password_protected(file_bytes):
        return fail(
            "This PDF is password_protected and cannot be processed. "
            "Please remove the password and re-upload."
        )
    
    log_step("✓ No password protection detected")

    # --- STEP 3: Register in Retry Queue --------------------------------------------------
    job_id = add_job(filename)
    log_step(f"Registered as job #{job_id} in processing queue")

    # --- STEP 4 & 5: Text Extraction or OCT --------------------------------------------------
    used_ocr = False
    extraction_method = "text"
    page_count = 0
    word_count = 0

    log_step("Analysing document - text-based or scanned?")
    scanned = is_scanned_pdf(file_bytes)

    if scanned:
        log_step(
            "Scanned PDF detected - running OCR. "
            "This may take 30-90 seconds depending on page count..."
        )
        try:
            document_text, page_count = run_ocr(file_bytes)
            word_count = len(document_text.split())
            used_ocr = True
            extraction_method = "ocr"
            log_step(
                f"✓ OCR complete: extracted ~{word_count:,} words "
                f"from {page_count} pages"
            )
        except Exception as e:
            return fail(f"OCR processing failed: {str(e)}", job_id=job_id)
    
    else:
        log_step("Text-based PDF detected - extracting text directly...")
        try:
            document_text, page_count, word_count = extract_text_from_pdf(file_bytes)
            log_step(
                f"✓ Text extracted: {word_count:,} words "
                f"from {page_count} pages"
            )
        except Exception as e:
            return fail (f"Text extraction failed: {str(e)}, job_id=job_id")
    
    # guard: did we get usable text?
    if len(document_text.strip()) < 50:
        return fail(
            "Could not extract meaningful text from this document. "
            "The file may be corrupted, blank, or contain only images "
            "without sufficient quality for OCR"
        )
    
    # --- STEP 6: Size Strategy --------------------------------------------------
    doc_length = len(document_text)
    strategy = get_document_size_strategy(document_text)

    log_step(
        f"Document size: {doc_length:,} chars"
        f"({word_count:,} words) -> strategy: {strategy}"
    )

    if strategy == "reject":
        return fail(
            f"Document is too large to process ({doc_length:,} chars). "
            f"Please split it into sections under ~300 pages and re-upload.",
            job_id=job_id,
            used_ocr=used_ocr
        )
    
    # --- STEP 7: Chunking (large documents only) --------------------------------------------------
    elif strategy == "chunk":
        log_step(
            "Large document - splitting at natural boundaries "
            "and summarizing each section. Nothing will be dropped..."
        )
        try:
            chunks = split_by_natural_boundaries(document_text)
            log_step(
                f"Split into {len(chunks)} chunks. "
                f"Summarizing each section with Claude..."
            )
            docuent_text = process_large_document(chunks, filename)
            log_step(
                f"✓ All {len(chunks)} sections summarized - "
                f"combined summary ready for extraction "
                f"({len(document_text):,} chars)"
            )
        except Exception as e:
            return fail(
                f"Chunk processing failed: {str(e)}",
                job_id=job_id,
                used_ocr=used_ocr
            )
     # --- STEP 8: LLM Extraction --------------------------------------------------
    log_step("Setting to Claude for structured extraction and analysis...")
    update_job(job_id, JobStatus.PROCESSING)

    extraction, error = extract_document_data(
        document_text=document_text,
        filename=filename,
        extraction_method=extraction_method,
        page_count=page_count,
        word_count=word_count
    )

    # --- STEP 9: Final Result --------------------------------------------------
    if extraction is None:
        return fail(error, job_id=job_id, used_ocr=used_ocr)
    
    flag_count = len(extraction.flags)
    critical_count = sum(
        1 for f in extraction.flags
        if f.severity.value == "critical"
    )

    log_step(
        f"✓ Extraction complete - "
        f"{extraction.document_type.value} detected, "
        f"confidence {extraction.confidence_score:.0%}, "
        f"{flag_count} flag(s) found"
        + (f" ({critical_count} critical)" if critical_count else "")
    )

    update_job(
        job_id,
        JobStatus.SUCCESS,
        result=extraction.model_dump(mode="json")
    )

    return ProcessingResult(
        status=ProcessingStatus.SUCCESS,
        extraction=extraction,
        job_id=job_id,
        used_ocr=used_ocr,
        file_info=file_info,
        processing_steps=steps
    )