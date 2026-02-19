"""Format extracted transactions into Telegram messages and CSV files."""

import io
import pandas as pd
from bot.parsers.llm_parser import Transaction


def format_transactions_message(transactions: list[Transaction]) -> str:
    """Return a human-readable summary for Telegram."""
    if not transactions:
        return "⚠️ No transactions found in the statement."

    lines = [f"✅ Found *{len(transactions)} transactions*\n"]
    total_debit = sum(t["amount"] for t in transactions if t["amount"] > 0)
    total_credit = sum(t["amount"] for t in transactions if t["amount"] < 0)

    for t in transactions:
        sign = "🔴" if t["amount"] > 0 else "🟢"
        lines.append(
            f"{sign} `{t['date']}` {t['description']}\n"
            f"   {t['currency']} {abs(t['amount']):.2f} ({t['type']})"
        )

    lines.append(f"\n📊 Total debits: *{total_debit:.2f}*")
    if total_credit < 0:
        lines.append(f"💚 Total credits: *{abs(total_credit):.2f}*")

    return "\n".join(lines)


def transactions_to_csv(transactions: list[Transaction]) -> io.BytesIO:
    """Return a CSV file (as BytesIO) from a list of transactions."""
    df = pd.DataFrame(transactions)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf
