import json
from fastapi.templating import Jinja2Templates

from utils.chatgptFunction import search_gpt



# ── Jinja2 templates ──────────────────────────────────────────────────────────
templates = Jinja2Templates(directory="templates")

from config.index import BASE_URL

# ── Shared constants ──────────────────────────────────────────────────────────
ANIMALS_DIR = "static/animals"

# =============================================================================
# DOG BREED
# =============================================================================

_DOG_SYSTEM_PROMPT = "You are a helpful AI assistant, who will help me with my research on animals and insects"


def _search_dog_info(breed: str) -> str:
    """Call GPT and return rendered dog.html fragment, or empty string on error."""
    prompt = f"""Give me the following information about {breed} dog breed in dictionary format. \
The response should only contain the dictionary object, properly formatted. \
There should be no data other than dict object:
    {{
    "Name": "value",
    "Other_Name": "value",
    "Origin": "value",
    "Breed_Group": "value",
    "Size": "value",
    "Type": "value",
    "Life_Span": "value",
    "Temperament": "value",
    "Height": "value",
    "Weight": "value",
    "Colors": "value"
    }}
    """
    try:
        info = search_gpt(prompt, _DOG_SYSTEM_PROMPT)
        info = info.replace('\n', '')
        if not info.strip().endswith('}'):
            info += '}'
        json_info = json.loads(info)
        return templates.get_template("dog.html").render(**json_info)
    except Exception as e:
        return ""


def dog_info_search(app, data: dict, return_data: list) -> None:
    """Thread target: fetch dog breed info + images and append to return_data."""
    try:
        dog_breeds = data.get('breeds', [])
        for breed in dog_breeds:
            dog_info = _search_dog_info(breed)
            return_data.append({
                'dog_breed': breed,
                'dog_info': dog_info,
                'dog_images': [],
            })
    except Exception as e:
        return_data.clear()


# =============================================================================
# INSECT
# =============================================================================

_INSECT_SYSTEM_PROMPT = "You are a helpful AI assistant, who will help me with my research on animals and insects"


def _search_insect_info(insect_name: str) -> str:
    """Call GPT and return rendered insects.html fragment, or empty string on error."""
    prompt = f"""Give me the following information about {insect_name} insect in dictionary format. \
The response should only contain the dictionary object, properly formatted. \
There should be no data other than dict object:
    {{
    "Common_Name": "value",
    "Scientific_Name": "value",
    "Size": "value",
    "Color": "value",
    "Shape": "value",
    "Habitat": "value",
    "Diet": "value",
    "Role_in_Ecosystem": "value",
    "Interesting_Fact": "value"
    }}
    """
    try:
        info = search_gpt(prompt, _INSECT_SYSTEM_PROMPT)
        if not info.strip().endswith('}'):
            info += '}'
        json_info = json.loads(info)
        html = templates.get_template("insects.html").render(**json_info)
        return html.replace('\n', '')
    except Exception as e:
        return ""


def find_insect_image_and_info(app, data: dict, return_data: list) -> None:
    """Thread target: fetch insect info and append to return_data."""
    try:
        insect_names = data.get('labels', [])
        for insect_name in insect_names:
            insect_info = _search_insect_info(insect_name)
            return_data.append({
                'insect_name': insect_name,
                'insect_info': insect_info,
                'insect_images': [],
            })
    except Exception as e:
        return_data.clear()


# =============================================================================
# SPIDER
# =============================================================================

_SPIDER_SYSTEM_PROMPT = "You are a helpful AI assistant, who will help me with my research on animals and insects"


def _search_spider_info(spider_name: str) -> str:
    """Call GPT and return rendered spiders.html fragment, or empty string on error."""
    prompt = f"""Give me the following information about {spider_name} spider in dictionary format. \
The response should only contain the dictionary object, properly formatted. \
There should be no data other than dict object:
    {{
    "Common_Name": "value",
    "Scientific_Name": "value",
    "Size": "value",
    "Color": "value",
    "Shape": "value",
    "Habitat": "value",
    "Diet": "value",
    "Role_in_Ecosystem": "value",
    "Interesting_Fact": "value"
    }}
    """
    try:
        info = search_gpt(prompt, _SPIDER_SYSTEM_PROMPT)
        if not info.strip().endswith('}'):
            info += '}'
        json_info = json.loads(info)
        html = templates.get_template("spiders.html").render(**json_info)
        return html.replace('\n', '')
    except Exception as e:
        return ""


def find_spider_image_and_info(app, data: dict, return_data: list) -> None:
    """Thread target: fetch spider info and append to return_data."""
    try:
        spider_names = data.get('labels', [])
        for spider_name in spider_names:
            spider_info = _search_spider_info(spider_name)
            return_data.append({
                'spider_name': spider_name,
                'spider_info': spider_info,
                'spider_images': [],
            })
    except Exception as e:
        return_data.clear()
