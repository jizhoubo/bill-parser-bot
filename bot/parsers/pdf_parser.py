"""Extract raw text from PDF bank/credit card statements."""

import logging
import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """Return concatenated text from all pages of a PDF."""
    pages_text = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                pages_text.append(text)
                logger.debug(f"Page {i + 1}: extracted {len(text)} chars")
    return "\n".join(pages_text)
