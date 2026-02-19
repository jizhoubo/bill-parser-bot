"""Use OpenAI structured outputs to extract transactions from raw statement text."""

import json
import logging
from typing import TypedDict
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI()

TRANSACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "transactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Transaction date, e.g. 2024-01-15"},
                    "description": {"type": "string", "description": "Merchant or transaction description"},
                    "amount": {"type": "number", "description": "Transaction amount (positive = debit, negative = credit/refund)"},
                    "currency": {"type": "string", "description": "3-letter currency code, e.g. SGD, USD"},
                    "type": {"type": "string", "enum": ["debit", "credit", "refund", "transfer", "fee", "unknown"]},
                },
                "required": ["date", "description", "amount", "currency", "type"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["transactions"],
    "additionalProperties": False,
}


class Transaction(TypedDict):
    date: str
    description: str
    amount: float
    currency: str
    type: str


def parse_transactions(raw_text: str) -> list[Transaction]:
    """Extract structured transactions from raw statement text using GPT-4o."""
    if not raw_text.strip():
        return []

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a financial data extractor. "
                    "Given raw text from a bank or credit card statement, "
                    "extract every transaction into structured JSON. "
                    "Use ISO date format (YYYY-MM-DD). "
                    "Amounts should be positive for debits/purchases, negative for credits/refunds. "
                    "If currency is ambiguous, infer from context or use SGD as default."
                ),
            },
            {"role": "user", "content": raw_text},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "transactions",
                "strict": True,
                "schema": TRANSACTION_SCHEMA,
            },
        },
    )

    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    transactions: list[Transaction] = data.get("transactions", [])
    logger.info(f"Extracted {len(transactions)} transactions")
    return transactions
