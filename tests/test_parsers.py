"""Basic unit tests for parsers and formatters."""

from unittest.mock import MagicMock, patch
from bot.parsers.llm_parser import parse_transactions
from bot.formatters import format_transactions_message, transactions_to_csv

SAMPLE_TRANSACTIONS = [
    {"date": "2024-01-15", "description": "GRAB FOOD", "amount": 18.50, "currency": "SGD", "type": "debit"},
    {"date": "2024-01-16", "description": "NTUC FAIRPRICE", "amount": 42.30, "currency": "SGD", "type": "debit"},
    {"date": "2024-01-17", "description": "CASHBACK REWARD", "amount": -5.00, "currency": "SGD", "type": "credit"},
]


def test_format_transactions_message():
    msg = format_transactions_message(SAMPLE_TRANSACTIONS)
    assert "3 transactions" in msg
    assert "GRAB FOOD" in msg
    assert "18.50" in msg


def test_format_empty():
    msg = format_transactions_message([])
    assert "No transactions" in msg


def test_transactions_to_csv():
    buf = transactions_to_csv(SAMPLE_TRANSACTIONS)
    content = buf.read().decode("utf-8")
    assert "date" in content
    assert "GRAB FOOD" in content
    assert "18.5" in content


@patch("bot.parsers.llm_parser.client")
def test_parse_transactions_mock(mock_client):
    import json
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({"transactions": SAMPLE_TRANSACTIONS})
    mock_client.chat.completions.create.return_value = mock_response

    result = parse_transactions("some raw text")
    assert len(result) == 3
    assert result[0]["description"] == "GRAB FOOD"


def test_parse_empty_text():
    result = parse_transactions("")
    assert result == []
