"""Extract transactions from statement images via GPT-4o Vision."""

import base64
import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI()

SYSTEM_PROMPT = """\
You are a financial data extractor. Given an image of a bank or credit card statement,
extract every transaction and return a JSON object with this exact schema:
{
  "bank_name": "<bank name or 'Unknown'>",
  "transactions": [
    {
      "date": "<YYYY-MM-DD>",
      "description": "<merchant or description>",
      "amount": <number, positive=debit/charge, negative=credit/refund>,
      "currency": "<3-letter code, e.g. SGD>"
    }
  ]
}
Return only valid JSON, no commentary."""


def parse_image(file_bytes: bytes, mime: str = "image/jpeg") -> tuple[list[dict], str, list[str]]:
    """
    Parse a statement image using GPT-4o Vision.

    Returns:
        transactions, bank_name, warnings
    """
    image_b64 = base64.b64encode(file_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                    {"type": "text", "text": "Extract all transactions from this statement."},
                ],
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=4096,
    )

    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    transactions = data.get("transactions", [])
    bank_name = data.get("bank_name", "Unknown")

    # normalize
    for t in transactions:
        t.setdefault("currency", "SGD")
        t["amount"] = float(t.get("amount", 0))

    warnings = []
    if bank_name == "Unknown":
        warnings.append("⚠️ Could not identify bank from image.")

    logger.info(f"GPT-4o Vision: {bank_name} → {len(transactions)} transactions")
    return transactions, bank_name, warnings
