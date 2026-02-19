"""Telegram bot handlers for /start, documents, photos, and plain text."""

import logging
import os
import tempfile

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.formatters import format_transactions_message, transactions_to_csv
from bot.parsers.image_parser import extract_text_from_image
from bot.parsers.llm_parser import parse_transactions
from bot.parsers.pdf_parser import extract_text_from_pdf

logger = logging.getLogger(__name__)

# Temp storage: chat_id -> last transactions list
_last_transactions: dict[int, list] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Hi! I'm *Bill Parser Bot*.\n\n"
        "Send me a bank or credit card statement and I'll extract all transactions for you.\n\n"
        "Supported formats:\n"
        "• 📄 PDF files\n"
        "• 🖼️ Images (JPG, PNG)\n"
        "• 📝 Pasted text\n\n"
        "Just drop the file here!",
        parse_mode="Markdown",
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.message.document
    if not doc:
        return

    mime = doc.mime_type or ""
    await update.message.reply_text("⏳ Parsing your statement, please wait...")

    with tempfile.NamedTemporaryFile(delete=False, suffix=_suffix(mime)) as tmp:
        file = await doc.get_file()
        await file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    try:
        if "pdf" in mime:
            raw_text = extract_text_from_pdf(tmp_path)
        elif "image" in mime:
            raw_text = extract_text_from_image(tmp_path)
        else:
            await update.message.reply_text("❌ Unsupported file type. Please send a PDF or image.")
            return

        await _reply_transactions(update, raw_text)
    finally:
        os.unlink(tmp_path)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.message.photo[-1]  # largest size
    await update.message.reply_text("⏳ Reading your statement image...")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        file = await photo.get_file()
        await file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    try:
        raw_text = extract_text_from_image(tmp_path)
        await _reply_transactions(update, raw_text)
    finally:
        os.unlink(tmp_path)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    if len(text) < 50:
        await update.message.reply_text(
            "ℹ️ Please send a longer text (paste your full statement), or upload a PDF/image."
        )
        return

    await update.message.reply_text("⏳ Parsing pasted statement text...")
    await _reply_transactions(update, text)


async def handle_csv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    transactions = _last_transactions.get(chat_id)
    if not transactions:
        await query.message.reply_text("⚠️ No transactions cached. Please re-upload your statement.")
        return

    csv_buf = transactions_to_csv(transactions)
    await query.message.reply_document(
        document=csv_buf,
        filename="transactions.csv",
        caption="📥 Here's your CSV export!",
    )


# ── helpers ──────────────────────────────────────────────────────────────────

async def _reply_transactions(update: Update, raw_text: str) -> None:
    chat_id = update.message.chat_id
    try:
        transactions = parse_transactions(raw_text)
    except Exception as e:
        logger.error(f"LLM parsing error: {e}")
        await update.message.reply_text(f"❌ Failed to parse transactions: {e}")
        return

    _last_transactions[chat_id] = transactions
    message = format_transactions_message(transactions)

    keyboard = [[InlineKeyboardButton("📥 Download CSV", callback_data="download_csv")]]
    reply_markup = InlineKeyboardMarkup(keyboard) if transactions else None

    await update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


def _suffix(mime: str) -> str:
    if "pdf" in mime:
        return ".pdf"
    if "png" in mime:
        return ".png"
    return ".jpg"
