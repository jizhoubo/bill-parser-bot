"""Format extracted transactions into Telegram messages and CSV files."""

import io

import pandas as pd


def format_transactions_message(transactions: list[dict], bank_name: str, warnings: list[str]) -> str:
    """Return a human-readable Telegram summary."""
    lines = []

    if warnings:
        lines.extend(warnings)
        lines.append("")

    if not transactions:
        lines.append("⚠️ No transactions found.")
        return "\n".join(lines)

    total_debit = sum(t["amount"] for t in transactions if t["amount"] > 0)
    total_credit = sum(t["amount"] for t in transactions if t["amount"] < 0)
    currency = transactions[0].get("currency", "SGD") if transactions else "SGD"

    lines.append(f"🏦 *{bank_name}* — {len(transactions)} transactions\n")

    for t in transactions:
        sign = "🔴" if t["amount"] > 0 else "🟢"
        lines.append(
            f"{sign} `{t['date']}` {t['description']}\n"
            f"   {t.get('currency', currency)} {abs(t['amount']):.2f}"
        )

    lines.append(f"\n📊 Debits: *{currency} {total_debit:,.2f}*")
    if total_credit < 0:
        lines.append(f"💚 Credits: *{currency} {abs(total_credit):,.2f}*")
    lines.append(f"💰 Net: *{currency} {(total_debit + total_credit):,.2f}*")

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
