"""Telegram bot handlers: /start, documents, photos, pasted text."""

import logging
import os
import tempfile

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.formatters import format_transactions_message, transactions_to_csv
from bot.parsers.image_parser import parse_image
from bot.parsers.llm_parser import parse_text
from bot.parsers.pdf_parser import parse_pdf

logger = logging.getLogger(__name__)

# Per-chat state: last parsed transactions + bank name
_last_result: dict[int, tuple[list[dict], str]] = {}
# Per-chat state: pending encrypted PDF bytes waiting for password
_pending_pdf: dict[int, bytes] = {}


# ── Commands ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Hi! I'm *Bill Parser Bot*.\n\n"
        "Send me a bank or credit card statement and I'll extract all transactions.\n\n"
        "Supported inputs:\n"
        "• 📄 PDF (DBS, OCBC, UOB, Maybank, HSBC, Standard Chartered, and more)\n"
        "• 🖼️ Image (JPG, PNG) — parsed via GPT-4o Vision\n"
        "• 📝 Pasted text — parsed via GPT-4o\n\n"
        "Password-protected PDFs: send the PDF first, then the password.",
        parse_mode="Markdown",
    )


# ── Document (PDF / generic file) ─────────────────────────────────────────────

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.message.document
    if not doc:
        return

    mime = doc.mime_type or ""
    chat_id = update.message.chat_id

    file = await doc.get_file()
    file_bytes = bytes(await file.download_as_bytearray())

    if "pdf" in mime or doc.file_name.lower().endswith(".pdf"):
        await _process_pdf(update, chat_id, file_bytes)
    elif "image" in mime:
        await _process_image(update, chat_id, file_bytes, mime)
    else:
        await update.message.reply_text("❌ Unsupported file. Please send a PDF or image.")


# ── Photo ─────────────────────────────────────────────────────────────────────

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.message.photo[-1]
    chat_id = update.message.chat_id
    file = await photo.get_file()
    file_bytes = bytes(await file.download_as_bytearray())
    await _process_image(update, chat_id, file_bytes, "image/jpeg")


# ── Text (pasted statement or PDF password) ───────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    chat_id = update.message.chat_id

    # Password for a pending encrypted PDF?
    if chat_id in _pending_pdf:
        pdf_bytes = _pending_pdf.pop(chat_id)
        await update.message.reply_text("🔑 Trying password...")
        await _process_pdf(update, chat_id, pdf_bytes, password=text)
        return

    if len(text) < 50:
        await update.message.reply_text(
            "ℹ️ Paste your full statement text, or upload a PDF / image."
        )
        return

    await update.message.reply_text("⏳ Parsing statement text...")
    try:
        transactions, bank_name, warnings = parse_text(text)
        await _send_result(update, chat_id, transactions, bank_name, warnings)
    except Exception as e:
        logger.error(f"Text parsing error: {e}")
        await update.message.reply_text(f"❌ Parse failed: {e}")


# ── CSV callback ──────────────────────────────────────────────────────────────

async def handle_csv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    result = _last_result.get(chat_id)
    if not result:
        await query.message.reply_text("⚠️ No cached transactions. Re-upload your statement.")
        return

    transactions, bank_name = result
    csv_buf = transactions_to_csv(transactions, bank_name)
    await query.message.reply_document(
        document=csv_buf,
        filename="transactions.csv",
        caption=f"📥 {bank_name} — {len(transactions)} transactions",
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _process_pdf(
    update: Update, chat_id: int, file_bytes: bytes, password: str | None = None
) -> None:
    await update.message.reply_text("⏳ Parsing PDF statement...")
    try:
        transactions, bank_name, warnings = parse_pdf(file_bytes, password)
        await _send_result(update, chat_id, transactions, bank_name, warnings)
    except ValueError as e:
        msg = str(e)
        if "password" in msg.lower():
            _pending_pdf[chat_id] = file_bytes
            await update.message.reply_text(
                f"🔒 {msg}\n\nReply with the password as a plain text message."
            )
        else:
            await update.message.reply_text(f"❌ {msg}")
    except Exception as e:
        logger.error(f"PDF parse error: {e}")
        await update.message.reply_text(f"❌ Failed to parse PDF: {e}")


async def _process_image(
    update: Update, chat_id: int, file_bytes: bytes, mime: str
) -> None:
    await update.message.reply_text("⏳ Reading statement image via GPT-4o Vision...")
    try:
        transactions, bank_name, warnings = parse_image(file_bytes, mime)
        await _send_result(update, chat_id, transactions, bank_name, warnings)
    except Exception as e:
        logger.error(f"Image parse error: {e}")
        await update.message.reply_text(f"❌ Failed to parse image: {e}")


async def _send_result(
    update: Update,
    chat_id: int,
    transactions: list[dict],
    bank_name: str,
    warnings: list[str],
) -> None:
    _last_result[chat_id] = (transactions, bank_name)
    message = format_transactions_message(transactions, bank_name, warnings)

    # Telegram has a 4096 char limit; truncate if needed
    if len(message) > 3800:
        lines = message.split("\n")
        truncated = "\n".join(lines[:60])
        message = truncated + f"\n\n… _(showing first 60 lines of {len(transactions)} transactions)_"

    keyboard = [[InlineKeyboardButton("📥 Download CSV", callback_data="download_csv")]] if transactions else None
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)
