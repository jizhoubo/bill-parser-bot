"""Parse bank statement PDFs using monopoly-core (rule-based, bank-aware)."""

import logging
from dataclasses import asdict

from monopoly.banks import BankDetector, banks
from monopoly.generic import GenericBank
from monopoly.pdf import MissingOCRError, PdfDocument, PdfParser
from monopoly.pipeline import Pipeline
from monopoly.statements.base import SafetyCheckError
from pydantic import SecretStr

logger = logging.getLogger(__name__)


def parse_pdf(file_bytes: bytes, password: str | None = None) -> tuple[list[dict], str, list[str]]:
    """
    Parse a bank statement PDF with monopoly-core.

    Returns:
        transactions: list of dicts with date/description/amount/polarity
        bank_name: detected bank name
        warnings: list of warning strings for the user
    """
    warnings = []
    document = PdfDocument(file_bytes=file_bytes)

    if document.is_encrypted:
        if not password:
            raise ValueError("PDF is password-protected. Please send the password as the next message.")
        document.authenticate(password)
        if document.is_encrypted:
            raise ValueError("Wrong password. Please try again.")

    analyzer = BankDetector(document)
    bank = analyzer.detect_bank(banks) or GenericBank
    bank_name = bank.__name__

    if bank_name == "GenericBank":
        warnings.append("⚠️ Unrecognized bank — using generic parser. Please review results carefully.")

    try:
        parser = PdfParser(bank, document)
        pipeline = Pipeline(parser, passwords=[SecretStr(password)] if password else [])
    except MissingOCRError:
        warnings.append("⚠️ No text layer found — attempting OCR (slow).")
        if cropbox := bank.pdf_config.page_bbox:
            for page in document:
                page.set_cropbox(cropbox)
        document = PdfParser.apply_ocr(document)
        parser = PdfParser(bank, document)
        pipeline = Pipeline(parser, passwords=[SecretStr(password)] if password else [])

    statement = pipeline.extract(safety_check=False)

    if statement.config.safety_check:
        try:
            statement.perform_safety_check()
        except SafetyCheckError:
            warnings.append("❗ Safety check failed — totals don't match. Transactions may be incomplete.")

    if not statement.config.safety_check:
        warnings.append(f"⚠️ {bank_name} statements have no safety check — please review results.")

    raw_transactions = pipeline.transform(statement)
    transactions = [_to_dict(t) for t in raw_transactions]
    logger.info(f"monopoly: {bank_name} → {len(transactions)} transactions")
    return transactions, bank_name, warnings


def _to_dict(t) -> dict:
    d = asdict(t) if hasattr(t, "__dataclass_fields__") else dict(t)
    # normalize polarity: credit = negative amount
    if d.get("polarity") == "CR" or d.get("polarity") == -1:
        d["amount"] = -abs(d["amount"])
    else:
        d["amount"] = abs(d["amount"])
    d.setdefault("currency", "SGD")
    return d
