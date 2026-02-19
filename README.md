# bill-parser-bot

A Telegram bot that extracts transactions from credit card and bank statement PDFs.

Built on [monopoly-core](https://github.com/benjamin-awd/monopoly) for rule-based bank-aware parsing, with GPT-4o Vision fallback for images.

## Supported Banks

| Bank | Credit | Debit |
|---|---|---|
| DBS / POSB | ✅ | ✅ |
| OCBC | ✅ | ✅ |
| UOB | ✅ | ✅ |
| Maybank | ✅ | ✅ |
| HSBC | ✅ | ❌ |
| Standard Chartered | ✅ | ❌ |
| Bank of America | ✅ | ✅ |
| Chase | ✅ | ❌ |
| Citibank | ✅ | ❌ |
| + others via [monopoly](https://github.com/benjamin-awd/monopoly) | | |

Unknown banks → GPT-4o fallback.

## Features

- 📄 **PDF statements** — monopoly-core (rule-based, bank-aware)
- 🖼️ **Image statements** — GPT-4o Vision OCR
- 📝 **Pasted text** — GPT-4o structured extraction
- 🔒 **Password-protected PDFs** — send PDF then reply with password
- 📥 **CSV export** — download all transactions

## Setup

```bash
# System dependencies (required for pdftotext)
sudo apt-get install build-essential libpoppler-cpp-dev pkg-config

# Install
git clone https://github.com/jizhoubo/bill-parser-bot.git
cd bill-parser-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env: BOT_TOKEN + OPENAI_API_KEY

# Run
python main.py
```

## Project Structure

```
bill-parser-bot/
├── bot/
│   ├── handlers.py          # Telegram handlers
│   ├── parsers/
│   │   ├── pdf_parser.py    # monopoly-core (primary)
│   │   ├── image_parser.py  # GPT-4o Vision
│   │   └── llm_parser.py    # GPT-4o text fallback
│   └── formatters.py
├── main.py
└── requirements.txt
```
