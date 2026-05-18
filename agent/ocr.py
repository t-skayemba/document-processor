import io
import os 
import logging 
from typing import Tuple, Optional
from PIL import Image 
import pytesseract

logger = logging.getLogger(__name__)

# Tesseract config: --oem 3 = best OCR engine, --psm 1 = suto page segmentation
TESSERACT_CONFIG = "--oem 3 --psm 1"

def ocr_pdf_with_tesseract(file_bytes: bytes) -> Tuple[str, int]:
    """
    Convert each PDF page to an image, then run Tesseract OCR on it.
    Returns: (full_extracted_text, page_count)
    """
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise ImportError(
            "pdf2image is required or OCR. Install it with: pip install pdf2image\n"
            "Also ensure poppler is installed: brew install poppler"
        )

    logger.info("Starting Tesseract OCR processing...")

    # Convert PDF pages to PIL Images at 300DPI (high quality for OCR)
    try:
        pages = convert_from_bytes(
            file_bytes,
            dpi=300,
            fmt="PNG"
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to convert PDF images: {e}\n"
            "Make sure poppler is insalled: brew install poppler"
        )
    
    page_count = len(pages)
    extracted_pages = []

    for i, page_image in enumerate(pages):
        logger.info(f"OCR processing page {i + 1}/{page_count}...")
        try:
            # run Tesseract on this page's image
            page_text = pytesseract.image_to_string(
                page_image,
                config=TESSERACT_CONFIG,
                lang="eng"
            )
            extracted_pages.append(page_text)
        except pytesseract.TesseractNotFoundError:
            raise RuntimeError(
                "Tesseract is not installed or not found in PATH.\n"
                "Fix: brew install tesseract"
            )
        except Exception as e:
            logger.warning(f"OCR failed on page {i + 1}: {e}. Skipping page.")
            extracted_pages.append(f"[OCR FAILED ON PAGE {i + 1}]")
        
    full_text = "\n\n--- PAGE BREAK --- \n\n".join(extracted_pages)
    logger.info(f"OCR complete. Extracted ~{len(full_text.split())} words from {page_count} pages.")

    return full_text, page_count

def ocr_pdf_with_textract(file_bytes: bytes) -> Tuple[str, int]:
    """
    Using the paid Textract with AWS
    More accuracte than Tesseract, but stored on the cloud
    Use when Tesseract quality is insufficient
    Returns: full_text, page_count
    Must have: 
        - pip install boto3
        - AWS credentials configured
        - AWS account with access to Textract
    """
    try:
        import boto3
    except ImportError:
        raise ImportError("boto3 required for Textract. Run: pip install boto3")
    
    client = boto3.client("textract", region_name=os.getenv("AWS_REGION", "us-east-1"))

    logger.info("Sending document to AWS Textract...")

    try:
        response = client.detect_document_text(
            Document={"Bytes": file_bytes}
        )
    except Exception as e:
        logger.warning(f"AWS Textract failed: {e}")
    
    # combine the LINE blocks

    lines = [
        block["Text"]
        for block in response.get("Blocks", [])
        if block["BlockType"] == "LINE"
    ]
    
    full_text = "\n".join(lines)

    page_count = 1

    logger.info(f"Textract extraction complete. Extracted {len(lines)} lines of text.")
    return full_text, page_count

def run_ocr(file_bytes: bytes) -> Tuple[str, int]:
    """
    Main OCR entry point. Picked the provider based on .env setting.
    Returns: full_text, page_count
    """
    provider = os.getenv("OCR_PROVIDER", "tesseract").lower()

    if provider == "textract":
        logger.info("Using AWS Textract for OCR")
        return ocr_pdf_with_textract(file_bytes)
    else:
        logger.info("Using Tesseract for OCR")
        return ocr_pdf_with_tesseract(file_bytes)