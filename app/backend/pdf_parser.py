"""
PDF Parser module with PyMuPDF primary extractor and Tesseract OCR fallback.
Extracts clean text, preserves page numbers, identifies headings, and detects scanned pages.
"""

import io
import fitz  # PyMuPDF
from typing import List, Dict, Any
from PIL import Image
from app.backend.config import TESSERACT_CMD

# Configure pytesseract if available and custom binary path is provided
try:
    import pytesseract
    if TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    HAS_PYTESSERACT = True
except Exception:
    HAS_PYTESSERACT = False


def extract_text_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Parses a PDF document page-by-page.
    Uses PyMuPDF as the primary fast extractor.
    Falls back to Tesseract OCR when a page contains little or no extractable text.
    
    Returns:
        {
            "page_count": int,
            "total_chars": int,
            "pages": [
                {
                    "page_number": int,
                    "text": str,
                    "extraction_method": str ("pymupdf" | "ocr_tesseract" | "fallback_empty"),
                    "char_count": int,
                    "headings": List[str]
                },
                ...
            ]
        }
    """
    doc = fitz.open(pdf_path)
    pages_data: List[Dict[str, Any]] = []
    total_chars = 0

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1

        # 1. Primary extraction via PyMuPDF
        text = page.get_text("text").strip()
        method = "pymupdf"
        headings = []

        # Extract blocks to find headings/section titles
        blocks = page.get_text("blocks")
        for b in blocks:
            block_text = b[4].strip()
            # Simple heuristic: short lines, numbered sections (e.g. "1. Overview", "2. Component: BrakeControlSWC")
            lines = block_text.split("\n")
            for line in lines:
                line_clean = line.strip()
                if (line_clean.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "Section", "AUTOSAR"))
                        and len(line_clean) < 100):
                    headings.append(line_clean)

        # 2. Check if text is insufficient (< 50 characters) -> Trigger OCR fallback
        if len(text) < 50:
            if HAS_PYTESSERACT:
                try:
                    pix = page.get_pixmap(dpi=200)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    ocr_text = pytesseract.image_to_string(img).strip()
                    if len(ocr_text) > len(text):
                        text = ocr_text
                        method = "ocr_tesseract"
                except Exception as e:
                    # If Tesseract binary is not installed on system, keep pymupdf text
                    if not text:
                        method = "fallback_empty"
            else:
                if not text:
                    method = "fallback_empty"

        char_count = len(text)
        total_chars += char_count

        pages_data.append({
            "page_number": page_num,
            "text": text,
            "extraction_method": method,
            "char_count": char_count,
            "headings": headings
        })

    doc.close()

    return {
        "page_count": len(pages_data),
        "total_chars": total_chars,
        "pages": pages_data
    }
