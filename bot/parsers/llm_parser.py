"""LLM fallback parser for pasted statement text via GPT-4o structured output."""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI()

TRANSACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "bank_name": {"type": "string"},
        "transactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "description": {"type": "string"},
                    "amount": {"type": "number", "description": "positive=debit, negative=credit/refund"},
                    "currency": {"type": "string"},
                },
                "required": ["date", "description", "amount", "currency"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["bank_name", "transactions"],
    "additionalProperties": False,
}


def parse_text(raw_text: str) -> tuple[list[dict], str, list[str]]:
    """
    Parse raw pasted statement text with GPT-4o structured output.

    Returns:
        transactions, bank_name, warnings
    """
    if not raw_text.strip():
        return [], "Unknown", []

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a financial data extractor. "
                    "Given raw text from a bank or credit card statement, "
                    "extract every transaction. "
                    "Dates should be YYYY-MM-DD. "
                    "Amounts: positive for debits/purchases, negative for credits/refunds. "
                    "Currency: infer from context, default SGD."
                ),
            },
            {"role": "user", "content": raw_text},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "statement_transactions",
                "strict": True,
                "schema": TRANSACTION_SCHEMA,
            },
        },
    )

    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    transactions = data.get("transactions", [])
    bank_name = data.get("bank_name", "Unknown")

    warnings = []
    if bank_name == "Unknown":
        warnings.append("⚠️ Could not identify bank from text.")

    logger.info(f"LLM text parser: {bank_name} → {len(transactions)} transactions")
    return transactions, bank_name, warnings
