from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from langdetect import detect
from openai import OpenAI
from translate import Translator

from database.database_config import (
    collection_by_topic,
    collection_by_type,
    collection_of_conversation,
    sort_orders,
)
from utils.urdu_ai_profile import get_role, prompts

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set; Urdu AI endpoints require it.")
        _client = OpenAI()
    return _client


def ensure_openai_configured() -> None:
    """Raises RuntimeError if OpenAI is not configured."""
    _get_client()


def detect_english(text):
    try:
        return detect(text) == "en"
    except Exception:
        return False


def save_prompt_in_db(
    system_prompt,
    user_prompt,
    username,
    user_time,
    character,
    check,
    character_name,
    gender,
):
    user_prompt_command = ""
    if check == "ai_chat":
        user_prompt_command = user_prompt

    json_data = {
        "username": username,
        "category": check,
        "character": character,
        "character_name": character_name,
        "user_prompt_command": user_prompt_command,
        "user_prompt_time": user_time,
        "system_prompt": system_prompt,
        "system_response_time": datetime.now().strftime("%d/%m/%Y - %H:%M:%S"),
    }
    if gender != "":
        json_data["gender"] = gender
    
    # For poetry by topic/type, store the search value for retrieval
    if check in ("by_type", "by_topic"):
        json_data["search_value"] = user_prompt

    if check == "by_type":
        result = collection_by_type.insert_one(json_data)
    elif check == "by_topic":
        result = collection_by_topic.insert_one(json_data)
    elif check == "ai_chat":
        result = collection_of_conversation.insert_one(json_data)
    else:
        return


def gen_ai_function(
    system_role,
    prompt,
    username,
    user_time,
    check,
    character,
    character_name,
    gender,
    translated_prompt,
):
    client = _get_client()
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": translated_prompt},
            ],
        )
        completed_data = completion.choices[0].message.content
        save_prompt_in_db(
            completed_data,
            prompt,
            username,
            user_time,
            character,
            check,
            character_name,
            gender,
        )
        return {"flag": True, "completion_data": completed_data}
    except Exception:
        return {"flag": False, "completion_data": ""}


def gen_ai_function_stream(
    system_role,
    prompt,
    username,
    user_time,
    user_value,
    check,
):
    client = _get_client()
    try:
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt},
            ],
            stream=True,
        )
        sentence = ""
        all_sentences = []  # Collect all sentences for database storage
        for chunk in stream:
            data = chunk.choices[0].delta.content
            if data is None and sentence != "":
                yield sentence
                all_sentences.append(sentence)
            if data is not None:
                if "]" not in data:
                    sentence += data
                else:
                    data = data.replace("]", "")
                    sentence += data
                    sentence = sentence.replace("\n", "")
                    sentence = sentence.replace("[", "")
                    if sentence != "":
                        sentence = sentence.rstrip()
                        if sentence.endswith(","):
                            sentence = sentence[:-1]
                        yield sentence
                        yield "\n"
                        all_sentences.append(sentence)
                    sentence = ""
        
        # Save the complete response to database after streaming completes
        if all_sentences:
            full_response = "\n".join(all_sentences)
            save_prompt_in_db(
                full_response,
                user_value,  # The topic or type that was searched
                username,
                user_time,
                "",  # character (not applicable for poetry by topic/type)
                check,  # "by_topic" or "by_type"
                "",  # character_name (not applicable)
                "",  # gender (not applicable)
            )
    except Exception:
        yield ""


def ai_conversation(data: dict) -> dict:
    username = data["username"]
    user_prompt_time = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
    translator = Translator(to_lang="ur")

    name = ""
    if data.get("name"):
        name = translator.translate(data["name"])

    gender = ""
    if data.get("gender"):
        gender = translator.translate(data["gender"])

    age = ""
    if data.get("age"):
        age = data["age"]

    prompt = data["prompt"]
    if detect_english(prompt):
        translated_prompt = translator.translate(prompt)
    else:
        translated_prompt = prompt

    number = ""
    character = data["character"]
    if character == "Ustad":
        character = "Urdu Scholar"

    if character == "Urdu Scholar":
        number = "3"
    elif character in "Dost":
        number = "5"
    elif character == "Competitor":
        number = "4"
    elif character == "Shayar":
        number = "2"

    character_in_urdu = translator.translate(character)
    system_role = get_role(number, character_in_urdu, name, gender, age)
    character = data["character"]

    try:
        ai_data = gen_ai_function(
            system_role,
            prompt,
            username,
            user_prompt_time,
            "ai_chat",
            character,
            name,
            gender,
            translated_prompt,
        )
        if ai_data["flag"]:
            return {"flag": True, "completion_data": ai_data["completion_data"]}
        return {"flag": False, "completion_data": ""}
    except Exception:
        return {"flag": False, "completion_data": ""}


def ai_conversation_with_poets(data: dict) -> dict:
    acquired = ai_conversation(data)
    if acquired["flag"]:
        return {"response": acquired["completion_data"]}
    return {"response": []}


def stream_ai_conversation(data: dict):
    """
    Same persona / translation setup as ai_conversation; yields plain text deltas.
    After a successful run, saves the full assistant text like the non-stream path.
    """
    username = data["username"]
    user_prompt_time = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
    translator = Translator(to_lang="ur")

    name = ""
    if data.get("name"):
        name = translator.translate(data["name"])

    gender = ""
    if data.get("gender"):
        gender = translator.translate(data["gender"])

    prompt = data["prompt"]
    if detect_english(prompt):
        translated_prompt = translator.translate(prompt)
    else:
        translated_prompt = prompt

    character = data["character"]
    if character == "Ustad":
        character = "Urdu Scholar"

    if character == "Urdu Scholar":
        number = "3"
    elif character in "Dost":
        number = "5"
    elif character == "Competitor":
        number = "4"
    elif character == "Shayar":
        number = "2"
    else:
        number = ""

    character_in_urdu = translator.translate(character)
    age = data.get("age") or ""
    system_role = get_role(number, character_in_urdu, name, gender, age)
    char_for_db = data["character"]

    client = _get_client()
    parts: list[str] = []
    try:
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": translated_prompt},
            ],
            stream=True,
        )
        for chunk in stream:
            choice = chunk.choices[0]
            if choice.delta.content:
                tok = choice.delta.content
                parts.append(tok)
                yield tok
        full = "".join(parts)
        if full:
            save_prompt_in_db(
                full,
                prompt,
                username,
                user_prompt_time,
                char_for_db,
                "ai_chat",
                name,
                gender,
            )
    except Exception:
        yield ""


def stream_poetry_by_topic(data: dict):
    prompt = prompts["4"].format(poetry_topic=data["poetry_topic"])
    system_role = get_role("1", "", "", "", "")
    username = data["username"]
    user_prompt_time = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
    user_value = data["poetry_topic"]
    return gen_ai_function_stream(
        system_role,
        prompt,
        username,
        user_prompt_time,
        user_value,
        "by_topic",
    )


def stream_poetry_by_type(data: dict):
    prompt = prompts["5"].format(poetry_type=data["poetry_type"])
    system_role = get_role("1", "", "", "", "")
    username = data.get("username") or ""
    user_prompt_time = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
    user_value = data["poetry_type"]
    return gen_ai_function_stream(
        system_role,
        prompt,
        username,
        user_prompt_time,
        user_value,
        "by_type",
    )


def get_chat_history(data: dict) -> dict:
    username = data["username"]
    items = []

    if data.get("poetry_topic"):
        topic = data["poetry_topic"]
        items = collection_by_topic.find({"username": username, "search_value": topic})
    elif data.get("poetry_type"):
        poetry_type = data["poetry_type"]
        items = collection_by_type.find({"username": username, "search_value": poetry_type})
    elif data.get("character"):
        character = data["character"]
        query_values = {"username": username, "character": character}
        if data.get("name"):
            query_values["character_name"] = data["name"]
        if data.get("gender"):
            query_values["gender"] = data["gender"]
        items = collection_of_conversation.find(query_values).sort(
            "user_prompt_time", sort_orders[1]
        )

    out = []
    for item in items:
        if "_id" in item:
            item["_id"] = str(item["_id"])
        out.insert(0, item)
    return {"items": out}


def delete_chat_history(data: dict) -> dict:
    if not data.get("username"):
        return {"info": "username required", "flag": False}
    username = data["username"]
    if not data.get("character"):
        return {"info": "character required", "flag": False}

    character = data["character"]
    query_values = {"username": username, "character": character}
    if data.get("name"):
        query_values["character_name"] = data["name"]
    if data.get("gender"):
        query_values["gender"] = data["gender"]

    result = collection_of_conversation.delete_many(query_values)
    return {
        "info": f"{result.deleted_count} document(s) deleted for username={username}, character={character}",
        "flag": True,
    }
