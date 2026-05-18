# 📄 DocAgent - Document Processing Agent

Stop missing issues in contracts and invoices. Start catching them instantly.

DocAgent is an AI-powered document analysis tool that processes PDFs (contracts, invoices, legal documents) and returns structured data, risk flags, and plain-English summaries.

🚀 **docagent.tianakayemba.dev** — no setup required, try it live!

---

# What It Does
Drop in any PDF DocAgent will:
- **Extract structured data** - pulls parties, dates, amounts, obligations, and clauses into clean JSON, ready to export or pipe into your systems.
- **Flag issues automatically** - detects math discrepancies, missing fields, risky clauses, one-sided terms, and missing signatures, ranked by severtiy
- **Summarise in plain English** - every document gets a 2-4 sentence summary a non-technical stakeholder can actually read
- **Handle scanned documents** - detects image-only PDFs and routes them through OCR automatically, no manual steps needed
- **Process large documents intelligently** - chunks oversize documetns at natural boundaries, summarises each section seperately, and combines them so nothing gets dropped
- **Retry bad extractions** - if the LLM returns malformed output, it cleans and retries with a progressively stricter prompt before giving up
- **Track every job** - all processing jobs are logged in SQLite with status, attempt count, and error messages for auditing and retry
- **Reject problem files early** - password-protected, corrupted, empty, and oversized files are caught before hitting the LLM, with clear error messages

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| AI | Anthropic Claude API (claude-sonnet-4-6) |
| UI | Streamlit |
| PDF Parsing | pdfplumber |
| OCR | Tesseract (local) / AWS Textract (cloud) |
| Output validation | Pydantic v2 |
| Job queue | SQLite |
| API retry logic | tenacity |
| PDF utilities | pikepdf, pdf2image, Pillow |

---

## How It Works
Every document goes through the same pipeline automatically:

```
Upload PDF
  ↓
Validate (size, type, magic bytes, password check)
  ↓
Detect: text-based or scanned?
  ├── Text    → extract directly with pdfplumber
  └── Scanned → run OCR (Tesseract or AWS Textract)
  ↓
Size strategy
  ├── Small  (< 60k chars)  → send directly to Claude
  ├── Large  (< 400k chars) → chunk → summarise each section → combine
  └── Huge   (> 400k chars) → reject with clear message
  ↓
Claude extracts structured JSON (up to 3 attempts, stricter prompt each retry)
  ↓
Pydantic validates output schema
  ↓
Return structured data + flags + summary
```

Scanned PDF detected uses multiple signals - image presence, text object count, character density relative to page area - so sparse-but-valid documents like cover pages and signature pages are not misidentified.

---

## Running Locally

### Prerequisites
- Python 3.11
- macOS: `brew install tesseract poppler`
- Windows: [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and [poppler](https://github.com/oschwartz10612/poppler-windows)

### 1. Clone the repo
```bash
git clone https://github.com/t-skayemba/document-processor
cd document-processor
```

### 2. Create a virtual environment
```bash
python3.11 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Set your environment variables
```bash
cp .env.example .env
```
Open `.env` and fill in your values:
ANTHROPIC_API_KEY=your_api_key_here
OCR_PROVIDER=tesseract
MAX_FILE_SIZE_MB=50
MAX_RETRIES=3

Get an Anthropic API key at [console.anthropic.com](https://console.anthropic.com)

### 5. Run the app
```bash
streamlit run app.py
```
Visit **http://localhost:8501**

---

## Enviornment Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `ANTHROPIC_API_KEY` | ✅ Yes | - | Your Anthropic API key |
| `OCR_PROVIDER` | No | `tesseract` | `tesseract` (free, local) or `textract` (AWS, paid)|
| `MAX_FILE_SIZE_MB` | No | `50` | Max upload size in MB |
| `MAX_RETRIES` | No | `3` | LLM retry attempts on bad output |
| `AWS_REGION` | Textract only | `us-east-1` | AWS region for Textract |

---

## Project Structure
```
document-processor/
├── app.py                    # Streamlit web UI
├── styles.py                 # CSS overrides + custom HTML components
├── requirements.txt
├── .env.example
├── agent/
│   ├── processor.py          # Main orchestrator — runs each step in order
│   ├── extractor.py          # Claude API calls + JSON retry logic
│   ├── ocr.py                # Tesseract or AWS Textract
│   └── retry_queue.py        # SQLite job tracking
├── models/
│   └── schemas.py            # Pydantic models for all document types
└── utils/
    └── file_utils.py         # Validation, OCR detection, chunking
```

---

## Edge Cases Handled

| Edge Case | How It's Handled |
| --- | --- |
| Scanned PDF | Multi-signal detection, auto-routed to OCR |
| Sparse text PDF (cover page, signature page) | Multi-signal detection avoids false OCR routing |
| Password protected PDF | Detected via pikepdf, rejected with clear message |
| Corrupted file | Magic byte check + exception handling at every stage |
| Large document (> 60k chars) | Chunked at natural boundaries, each section summarized |
| Oversized segment within a chunk | Sentence split → clause split → hard cut fallback chain |
| Enormous document (> 400k chars) | Rejected cleanly with instructions to split |
| LLM returns bad JSON | Regex cleanup attempted, then strict retry prompt |
| LLM rate limit | Exponential backoff via tenacity (2s → 4s → 8s) | Chunk summarisation failure | Raw chunk included as fallback - nothing silently lost |
| Empty document | Caught post-extraction, rejected before hitting LLM |

---

## Supported Document Types

| Type | What Gets Extracted |
| --- | --- |
| Invoice | Vendor, client, line items, totals, tax, due date, payment terms |
| Contract | Parties, dates, obligations, termination clauses, jurisdiction, auto-renewal |
| Legal | Governing law, liability, indemnifation, non-compete, confidentiality |
| Financial | Key figures, dates, entities, summary |
| Receipt | Vendor, amounts, items, date |

---

## Data & Privacy
| What | Where |
| --- | --- |
| Uploaded PDFs | Processed in memory only - never written to disk |
| Job logs | Stored locally in SQLite (`retry_queue.db`) |
| Extracted data | Reatured to UI only - not persisted unless you add storage |
| Document text | Sent to Anthropic's API for analysis |

Document content is sent to Anthropic's API for answer generation. See [Anthropic's Privacy Policy](https://www.anthropic.com/privacy) for details.

---

## Extending this Project

**Add more document types**
**Add more document types**
Add a new Pydantic model to `models/schemas.py` and update the
extraction prompt in `agent/extractor.py`.

**Switch to AWS Textract**
Set `OCR_PROVIDER=textract` in `.env`. No code changes needed.
Use Textract when documents have complex tables, poor scan quality,
or handwriting.

**Production job queue**
Replace SQLite in `agent/retry_queue.py` with Redis + Celery
for high-volume deployments.

**REST API**
Wrap `agent/processor.py` in FastAPI. The processor is already
fully decoupled from the UI — takes bytes in, returns a dataclass out.

**Batch processing**
Add a folder-watch mode using `watchdog` to automatically process
documents dropped into a directory.

---

## Why Python 3.11?
Several dependencies (Pillow, pikepdf, pdfplumber) compile C extensions
not yet compatible with Python 3.13+. Python 3.11 is the current stable
sweet spot — fully supported by every package in this project.

---

## Deploying This for Your Business
Want DocAgent running with your knowledge base, your document types,
and your team's workflows connected?

📩 tskayemba@gmail.com

---

Built by Tiana Kayemba - [tianakayemba.dev](https://www.tianakayemba.dev/)

MIT License