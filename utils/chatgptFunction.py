import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Uses the dedicated BP_REPORT_KEY from .env
_api_key = os.getenv("BP_REPORT_KEY") or os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=_api_key)


def search_gpt(prompt: str) -> str:
    """
    Send a prompt to GPT and return the raw text response.
    Returns an empty string on failure.
    """
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful Physician who will help me "
                        "with how to improve health outcomes."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"[chatgptFunction] GPT error: {e}")
        return ""
