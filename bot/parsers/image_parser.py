"""Extract raw text from statement images via GPT-4o Vision."""

import base64
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI()


def extract_text_from_image(file_path: str) -> str:
    """Send image to GPT-4o Vision and return extracted statement text."""
    with open(file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "This is a bank or credit card statement. "
                            "Please extract all the transaction lines exactly as they appear, "
                            "preserving dates, amounts, and descriptions. "
                            "Return only the raw transaction text, no commentary."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
            }
        ],
        max_tokens=4096,
    )

    text = response.choices[0].message.content or ""
    logger.debug(f"Image OCR returned {len(text)} chars")
    return text
