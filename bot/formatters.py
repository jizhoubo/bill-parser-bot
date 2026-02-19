"""Format extracted transactions into Telegram messages and CSV files.

Uses HTML parse mode to avoid Markdown special-character issues.
"""

import html
import io

import pandas as pd

# Parse mode to pass to reply_text
PARSE_MODE = "HTML"


def format_transactions_message(transactions: list[dict], bank_name: str, warnings: list[str]) -> str:
    """Return an HTML-formatted Telegram summary (safe for any transaction description)."""
    lines = []

    if warnings:
        for w in warnings:
            lines.append(html.escape(w))
        lines.append("")

    if not transactions:
        lines.append("⚠️ No transactions found.")
        return "\n".join(lines)

    total_debit = sum(t["amount"] for t in transactions if t["amount"] > 0)
    total_credit = sum(t["amount"] for t in transactions if t["amount"] < 0)
    currency = transactions[0].get("currency", "SGD") if transactions else "SGD"

    lines.append(f"🏦 <b>{html.escape(bank_name)}</b> — {len(transactions)} transactions\n")

    for t in transactions:
        sign = "🔴" if t["amount"] > 0 else "🟢"
        desc = html.escape(str(t.get("description", "")))
        cur = html.escape(str(t.get("currency", currency)))
        lines.append(
            f"{sign} <code>{t['date']}</code> {desc}\n"
            f"   {cur} {abs(t['amount']):.2f}"
        )

    lines.append(f"\n📊 Debits: <b>{currency} {total_debit:,.2f}</b>")
    if total_credit < 0:
        lines.append(f"💚 Credits: <b>{currency} {abs(total_credit):,.2f}</b>")
    lines.append(f"💰 Net: <b>{currency} {(total_debit + total_credit):,.2f}</b>")

    return "\n".join(lines)


def transactions_to_csv(transactions: list[dict], bank_name: str) -> io.BytesIO:
    """Return a CSV BytesIO from transactions list."""
    rows = []
    for t in transactions:
        rows.append({
            "date": t.get("date", ""),
            "description": t.get("description", ""),
            "amount": t.get("amount", 0),
            "currency": t.get("currency", "SGD"),
            "bank": bank_name,
        })
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf
