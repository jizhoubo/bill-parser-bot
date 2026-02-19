"""Parse bank statement PDFs using monopoly-core (rule-based, bank-aware).

Falls back to pdfplumber + GPT-4o when monopoly fails.
"""

import logging
from dataclasses import asdict

import pdfplumber
from monopoly.banks import BankDetector, banks
from monopoly.generic import GenericBank
from monopoly.pdf import MissingOCRError, PdfDocument, PdfParser
from monopoly.pipeline import Pipeline
from monopoly.statements.base import SafetyCheckError
from pydantic import SecretStr

from bot.parsers.llm_parser import parse_text

logger = logging.getLogger(__name__)


def parse_pdf(file_bytes: bytes, password: str | None = None) -> tuple[list[dict], str, list[str]]:
    """
    Parse a bank statement PDF.

    Strategy:
      1. Try monopoly-core (bank-aware, rule-based)
      2. On failure: extract text with pdfplumber → GPT-4o LLM fallback

    Returns:
        transactions, bank_name, warnings
    """
    warnings: list[str] = []

    # ── Unlock encrypted PDF ──────────────────────────────────────────────────
    document = PdfDocument(file_bytes=file_bytes)
    if document.is_encrypted:
        if not password:
            raise ValueError("PDF is password-protected. Please send the password as a reply.")
        document.authenticate(password)
        if document.is_encrypted:
            raise ValueError("Wrong password. Please try again.")

    # ── Attempt 1: monopoly-core ──────────────────────────────────────────────
    try:
        transactions, bank_name, mono_warnings = _parse_with_monopoly(document, password)
        warnings.extend(mono_warnings)
        return transactions, bank_name, warnings

    except Exception as e:
        logger.warning(f"monopoly failed ({type(e).__name__}: {e}), falling back to LLM")
        warnings.append(f"⚠️ Bank-specific parser failed ({e}). Using GPT-4o fallback.")

    # ── Attempt 2: pdfplumber text → GPT-4o ──────────────────────────────────
    try:
        raw_text = _extract_text_pdfplumber(file_bytes)
        if not raw_text.strip():
            raise ValueError("No text could be extracted from PDF.")
        transactions, bank_name, llm_warnings = parse_text(raw_text)
        warnings.extend(llm_warnings)
        return transactions, bank_name, warnings

    except Exception as e:
        logger.error(f"LLM fallback also failed: {e}")
        raise RuntimeError(f"Could not parse PDF: {e}") from e


# ── Internal helpers ──────────────────────────────────────────────────────────

def _parse_with_monopoly(
    document: PdfDocument, password: str | None
) -> tuple[list[dict], str, list[str]]:
    warnings: list[str] = []

    analyzer = BankDetector(document)
    bank = analyzer.detect_bank(banks) or GenericBank
    bank_name = bank.__name__

    if bank_name == "GenericBank":
        warnings.append("⚠️ Unrecognized bank — using generic parser. Please review results carefully.")

    try:
        parser = PdfParser(bank, document)
        pipeline = Pipeline(parser, passwords=[SecretStr(password)] if password else [])
    except MissingOCRError:
        warnings.append("⚠️ No text layer found — applying OCR (slow).")
        if cropbox := bank.pdf_config.page_bbox:
            for page in document:
                page.set_cropbox(cropbox)
        document = PdfParser.apply_ocr(document)
        parser = PdfParser(bank, document)
        pipeline = Pipeline(parser, passwords=[SecretStr(password)] if password else [])

    # extract WITHOUT safety check to avoid total-mismatch errors,
    # but still raises ValueError if no transactions or no statement date
    statement = pipeline.extract(safety_check=False)

    if statement.config.safety_check:
        try:
            statement.perform_safety_check()
        except SafetyCheckError:
            warnings.append("❗ Safety check failed — totals don't match. Transactions may be incomplete.")

    raw_txns = pipeline.transform(statement)
    transactions = [_to_dict(t) for t in raw_txns]
    logger.info(f"monopoly: {bank_name} → {len(transactions)} transactions")
    return transactions, bank_name, warnings


def _extract_text_pdfplumber(file_bytes: bytes) -> str:
    import io
    pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n".join(pages)


def _to_dict(t) -> dict:
    d = asdict(t) if hasattr(t, "__dataclass_fields__") else dict(t)
    if d.get("polarity") == "CR" or d.get("polarity") == -1:
        d["amount"] = -abs(d["amount"])
    else:
        d["amount"] = abs(d["amount"])
    d.setdefault("currency", "SGD")
    return d
