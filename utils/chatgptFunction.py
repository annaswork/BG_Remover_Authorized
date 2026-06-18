import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Uses the dedicated BP_REPORT_KEY from .env
_api_key = os.getenv("BP_REPORT_KEY") or os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=_api_key)


def search_gpt(prompt: str, system_prompt: str, json_mode: bool = False) -> str:
    """
    Send a prompt to GPT and return the raw text response.
    Pass json_mode=True to enable response_format={'type': 'json_object'},
    which forces GPT to return a valid JSON string (no markdown, no prose).
    Returns an empty string on failure.
    """
    try:
        # OpenAI requires the word "json" to appear in messages when
        # response_format=json_object is used, otherwise it returns a 400.
        effective_system = (
            system_prompt + " Always respond with a valid JSON object."
            if json_mode
            else system_prompt
        )

        kwargs = dict(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": effective_system},
                {"role": "user", "content": prompt},
            ],
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        completion = client.chat.completions.create(**kwargs)
        return completion.choices[0].message.content
    except Exception as e:
        print(f"[chatgptFunction] GPT error: {e}")
        return ""
