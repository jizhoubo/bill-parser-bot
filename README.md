# bill-parser-bot

A Telegram bot that extracts transactions from credit card and bank statements.

## Features

- 📄 **PDF statements** — text extraction via `pdfplumber`
- 🖼️ **Image statements** — OCR via GPT-4o Vision
- 📝 **Pasted text** — direct LLM parsing
- 📊 **Structured output** — date, description, amount, currency, type
- 📥 **CSV export** — download transactions as a spreadsheet

## Setup

```bash
# 1. Clone and install
git clone https://github.com/jizhoubo/bill-parser-bot.git
cd bill-parser-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env: add BOT_TOKEN and OPENAI_API_KEY

# 3. Run
python main.py
```

## Environment Variables

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token from [@BotFather](https://t.me/BotFather) |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o parsing |

## Project Structure

```
bill-parser-bot/
├── bot/
│   ├── handlers.py          # Telegram message/file handlers
│   ├── parsers/
│   │   ├── pdf_parser.py    # PDF → text (pdfplumber)
│   │   ├── image_parser.py  # Image → text (GPT-4o Vision)
│   │   └── llm_parser.py    # Text → structured transactions (GPT-4o)
│   └── formatters.py        # Transaction formatting + CSV export
├── tests/
│   └── test_parsers.py
├── main.py
├── .env.example
└── requirements.txt
```

## Usage

1. Start a chat with your bot
2. Send `/start` for instructions
3. Upload a PDF/image statement, or paste statement text
4. Bot replies with extracted transactions
5. Tap **Download CSV** to export
