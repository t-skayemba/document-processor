import os
import io
import logging
from pathlib import Path
from typing import Tuple, Optional
import pikepdf
import pdfplumber

logger = logging.getLogger(__name__)

# Maximum file size (configurable via .env, defaults to 50MB)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_MIME_TYPES = {"application/pdf"}

SINGLE_PASS_LIMIT = 60_000
CHUNK_LIMIT = 400_000
CHUNK_SIZE = 20_000
CHUNK_OVERLAP = 500

def validate_file(file_bytes: bytes, filename: str) -> Tuple[bool, str]:
    """
    Gate #1: run basic sanity checks before any processing
    returns (is_valid, error_message)
    """
    # check extension
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' not supported. Only PDF files are accepted."

    # check file size
    file_size = len(file_bytes)
    if file_size == 0:
        return False, "File is empty (0 bytes). Please upload a valid PDF."
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        return False, f"File size is too large ({size_mb:.1f}MB). Maximum allowed: {MAX_FILE_SIZE_MB}MB."
    
    # check PDF magic bytes - real PDFs start with "%PDF"
    if not file_bytes.startswith(b"%PDF"):
        return False, "File does not appear to be a valid PDF (missing PDF header)."
    
    return True, ""

def is_password_protected(file_bytes: bytes) -> bool:
    """
    Detect if a PDF requires a password to open.
    Use pikepdf which handles encrypted PDFs cleanly.
    """
    try:
        pikepdf.open(io.BytesIO(file_bytes))
        return False # opened successfully - not protected
    except pikepdf.PasswordError:
        return True # password required
    except Exception as e:
        logger.warning(f"Could not determine password protection status: {e}")
        return False

def is_scanned_pdf(file_bytes: bytes, text_threshold: int = 100) -> bool:
    """
    Determine if a PDF is a scanned image (no selectable text) vs a text PDF.
    Uses multiple signals.
    """
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            page_count = len(pdf.pages)
            if page_count == 0:
                return False
            
            pages_to_check = min(3, page_count)
            text_char_counts = []
            image_only_pages = 0

            for i in range(pages_to_check):
                page = pdf.pages[i]
                text = page.extract_text() or ""
                chars = len(text.strip())
                text_char_counts.append(chars)

                # Signal 1: does the page have images?
                has_images = len(page.images) > 0

                # Signal 2: does the page have any text objects at all?
                has_text_objects = len(page.chars) > 0

                # A scanned page typically has images but zero text objects
                if has_images and not has_text_objects:
                    image_only_pages += 1
            
            # Signal 3: average chars per page
            avg_chars = sum(text_char_counts) / len(text_char_counts)

            # Signal 4: ratio of chars to page dimensions (text density)
            # A real text page should have reasonable density
            sample_page = pdf.pages[0]
            page_area = (sample_page.width or 600) * (sample_page.height or 800)
            # roughly how many chars per 100,000 sq points we'd expect
            char_density = (avg_chars / page_area) * 100_000

            # Decision logic - needs MULTIPLE signals to call it scanned:
            # - Most checked pages or image-pnly with no text objects, OR
            # - Virtually no text AND images are present on the page
            majority_image_only = image_only_pages >= (pages_to_check * 0.6)
            suspiciously_sparse = avg_chars < 20 and char_density < 1.0

            return majority_image_only or suspiciously_sparse
        
    except Exception as e:
        logger.warning(f"Cound not determine is PDF is scanned: {e}")
        return True # fail safe

def extract_text_from_pdf(file_bytes: bytes) -> Tuple[str, int, int]:
    """
    Extract text directly from a text-based PDF (not scanned).
    Returns: (full_text, page_count, word_count)
    """
    full_text = []
    page_count = 0

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
    combined = "\n\n--- PAGE BREAK ---\n\n".join(full_text)
    word_count = len(combined.split())
    return combined, page_count, word_count

def get_document_size_strategy(text: str) -> str:
    """
    Decide how to handle a document based on its size.
    Returns: "single" | "chunk" | "reject"
    """
    length = len(text)
    if length <= SINGLE_PASS_LIMIT:
        return "single"
    elif length <= CHUNK_LIMIT:
        return "chunk"
    else:
        return "reject"

def split_by_natural_boundaries(text: str) -> list[str]:
    """
    Split a document at natural boundaries (page breaks -> paragraphs)
    rather than arbitary character counts.
    A clause or sentence never gets cut in half.
    """
    # Prefer page breaks inserted during PDF extraction
    if "--- PAGE BREAK ---" in text:
        segments = text.split("--- PAGE BREAK ---")
    else:
        segments = text.split("\n\n")
    
    chunks = []
    current_chunk = ""

    for segment in segments:
        if len(segment) > CHUNK_SIZE:
            sub_segments = _split_oversized_segment(segment)
        else:
            sub_segments = [segment]
        for sub in sub_segments:
            proposed = current_chunk + "\n\n" + sub if current_chunk else sub
            if len(proposed) > CHUNK_SIZE:
                # current chunk is full - save it and start a new one
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                overlap_text = current_chunk[-CHUNK_OVERLAP:] if current_chunk else ""
                current_chunk = overlap_text + "\n\n" + sub
            else:
                current_chunk = proposed
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def _split_oversized_segment(segment: str) -> list[str]:
    """
    A single segment is too large for one chunk.
    Try progressively cruder points until it fits:
    1. Sentence boundaries (". " or ".\n")
    2. Claude boundaries ("; " or ", ")
    3. Hard character cut (last resort)
    """
    import re

    # try sentence splits
    sentences = re.split(r'(?<=[.!?])\s+', segment)

    if len(sentences) > 1:
        return _regroup_into_chunks(sentences)
    
    # try clause splits
    clauses = re.split(r'(?<=;)\s+|(?<=,)\s+', segment)

    if len(clauses) > 1:
        return _regroup_into_chunks(clauses)
    
    logger.warning(
        f"Segment of {len(segment)} chars has no split points - "
        f"falling back to hard character cut."
    )
    parts = []
    start = 0
    while start < len(segment):
        end = start + CHUNK_SIZE
        parts.append(segment[start:end])
        start = end - CHUNK_OVERLAP
    return parts

def _regroup_into_chunks(pieces: list[str]) -> list[str]:
    """
    Take a list of small pieces (sentences or clauses) and regroup them
    into CHUNK_SIZE-sized chunks with overlap.
    """
    chunks = []
    current = ""

    for piece in pieces:
        proposed = current + " " + piece if current else piece

        if len(proposed) > CHUNK_SIZE:
            if current.strip():
                chunks.append(current.strip())
            overlap_text = current[-CHUNK_OVERLAP:] if current else ""
            current = overlap_text + " " + piece
        else:
            current = proposed
    
    if current.strip():
        chunks.append(current.strip())
    
    return chunks

def get_file_info(file_bytes: bytes, filename: str) -> dict:
    """Return a simple info dict about the file - usefil for logging and UI display."""
    size_kb = len(file_bytes) / 1024
    return {
        "filename": filename,
        "size_kb": round(size_kb, 1),
        "size_mb": round(size_kb / 1024, 2),
    }