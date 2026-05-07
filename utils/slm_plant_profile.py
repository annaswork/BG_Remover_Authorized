"""
slm_plant_profile.py
--------------------
Standalone module for generating botanical plant profiles via OpenAI.

Import and use in any FastAPI (or other) app.

Usage:
    from utils.slm_plant_profile import PlantProfiler
    
    profiler = PlantProfiler()          # call once at startup
    await profiler.startup()            # initializes httpx client + loads cache
    
    profile = await profiler.get_profile(
        scientific_name="Rosa canina",
        family="Rosaceae",
        genus="Rosa"
    )
    
    await profiler.shutdown()           # call on app shutdown
"""

import os
import re
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Defaults / constants
# ---------------------------------------------------------------------------
_CACHE_FILE = "slm_cache.json"
_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_MODEL = "gpt-4o-mini"
_TIMEOUT = 30.0

_SYSTEM_MSG = (
    "Botanical JSON API. Output only valid JSON. No markdown, preamble, or explanation.\n"
    "You may ONLY generate profiles for: plants, vegetables, fruits, and fungi.\n"
    "If the requested name is NOT a plant/vegetable/fruit/fungus, output an empty JSON object: {}.\n"
    "RULE: 'watering' and 'humidity' MUST be exactly 3 words."
)

_USER_MSG_TEMPLATE = (
    "Generate a botanical JSON profile for {name} ({family}, {genus}).\n\n"
    "Fields:\n"
    "common_name, description (1-2 sentences), taxonomy (Family, Genus),\n"
    "care_frequency (1-5/5), temperature_celsius, fertilizer, sunlight,\n"
    "watering (EXACTLY 3 words, e.g. 'Water once weekly'),\n"
    "humidity (EXACTLY 3 words, e.g. 'High humidity needed'),\n"
    "location, pruning, insects, soil_type, growth_rate (Slow/Moderate/Fast),\n"
    "hardiness_zones (USDA), toxicity, allergies_hazards, companions (2-3),\n"
    "problems (JSON array of 2-3 items)\n\n"
    'Example: {{"common_name":"Rose","description":"Fragrant flowering shrub.",'
    '"taxonomy":"Rosaceae, Rosa","care_frequency":"4/5","temperature_celsius":"15-25°C",'
    '"fertilizer":"Monthly","sunlight":"Full sun","watering":"Water once weekly",'
    '"humidity":"Moderate humidity needed","location":"Gardens","pruning":"Late winter",'
    '"insects":"Aphids","soil_type":"Loamy","growth_rate":"Moderate","hardiness_zones":"5-9",'
    '"toxicity":"None","allergies_hazards":"Thorns cause punctures; heavy pollen.",'
    '"companions":"Lavender, Garlic","problems":["Black spot","Mildew"]}}\n\n'
    "Output JSON for {name}:"
)

_FALLBACK_PROFILE = {
    "common_name": None,
    "description": None,
    "taxonomy": None,
    "care_frequency": "N/A",
    "sunlight": "N/A",
    "watering": "N/A",
    "humidity": "N/A",
    "location": "N/A",
    "temperature_celsius": "N/A",
    "fertilizer": "N/A",
    "pruning": "N/A",
    "insects": "N/A",
    "soil_type": "N/A",
    "growth_rate": "N/A",
    "hardiness_zones": "N/A",
    "toxicity": "N/A",
    "allergies_hazards": "N/A",
    "companions": "N/A",
    "problems": [],
}


# ---------------------------------------------------------------------------
# Helper: JSON parsing
# ---------------------------------------------------------------------------
def _clean_slm_text(raw: str) -> str:
    """Strip <think> blocks, markdown fences, and surrounding whitespace."""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    text = re.sub(r"```(?:json)?\s*", "", text)
    return text.strip()


def _try_parse_json(text: str) -> dict | None:
    """Attempt multiple strategies to extract a JSON object from raw text."""
    cleaned = _clean_slm_text(text)

    # Strategy 1 – direct parse
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2 – find outermost { ... } via brace counting
    start = cleaned.find("{")
    if start != -1:
        depth, end = 0, start
        for i in range(start, len(cleaned)):
            if cleaned[i] == "{":
                depth += 1
            elif cleaned[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        candidate = cleaned[start : end + 1]
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 3 – fix trailing commas
        fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            return json.loads(fixed)
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def _is_in_domain_name(name: str) -> bool:
    """
    Lightweight domain gate to avoid serving obviously non-botanical cached entries.
    This is intentionally conservative; the primary validation happens at the API layer.
    """
    n = (name or "").strip().lower()
    if not n:
        return False
    banned = {
        "cat",
        "dog",
        "horse",
        "cow",
        "goat",
        "sheep",
        "pig",
        "lion",
        "tiger",
        "bear",
        "fish",
        "bird",
        "human",
        "car",
        "phone",
        "laptop",
        "chair",
        "table",
    }
    if n in banned:
        return False
    return True


def _canonical_cache_name(name: str) -> str:
    """
    Canonicalize cache keys so minor user formatting differences don't cost tokens.
    Example: "snake plant" and "snakeplant" should map to the same cache entry.
    """
    n = (name or "").strip().lower()
    # Remove whitespace/hyphen/underscore entirely.
    n = re.sub(r"[\s\-_]+", "", n)
    return n


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------
class PlantProfiler:
    """
    Generates botanical profiles using OpenAI, with in-memory + disk caching.

    Parameters
    ----------
    api_key : str, optional
        OpenAI API key. Falls back to the OPENAI_API_KEY env variable.
    base_url : str, optional
        Base URL for the OpenAI-compatible endpoint.
    model : str, optional
        Chat model to use (default: gpt-4o-mini).
    cache_file : str, optional
        Path to the JSON file used for persistent caching.
    max_connections : int, optional
        Max simultaneous HTTP connections in the connection pool.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = _MODEL,
        cache_file: str = _CACHE_FILE,
        max_connections: int = 10,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("No OpenAI API key provided. Pass api_key= or set OPENAI_API_KEY.")

        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", _DEFAULT_BASE_URL)).rstrip("/")
        self.model = model
        self.cache_file = cache_file
        self.max_connections = max_connections

        self._client: httpx.AsyncClient | None = None
        self._cache: dict = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def startup(self) -> None:
        """Initialize the HTTP client and load the on-disk cache."""
        self._client = httpx.AsyncClient(
            timeout=None,
            limits=httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=max(1, self.max_connections // 2),
            ),
        )
        self._load_cache()
        print(f"[PlantProfiler] Ready — {len(self._cache)} cached profiles loaded.")

    async def shutdown(self) -> None:
        """Close the HTTP client and flush the cache to disk."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._save_cache()
        print("[PlantProfiler] Shutdown complete.")

    # ------------------------------------------------------------------
    # Botanical Validation
    # ------------------------------------------------------------------
    async def is_botanical(self, query: str) -> tuple[bool, str]:
        """
        Check if a query is about plants, vegetables, fruits, or fungus.
        Returns (is_valid, reason)
        """
        if not query or not query.strip():
            return False, "Empty query"
        
        validation_prompt = (
            f"Is '{query}' a plant, vegetable, fruit, or fungus? "
            "Answer with ONLY 'YES' or 'NO' followed by a brief reason."
        )
        
        try:
            res = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a botanical classifier. Answer only YES or NO."},
                        {"role": "user", "content": validation_prompt},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 50,
                },
                timeout=_TIMEOUT,
            )
            
            if res.status_code == 200:
                content = res.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                is_valid = content.upper().startswith("YES")
                return is_valid, content
        except Exception as exc:
            print(f"[PlantProfiler] Validation error: {exc}")
            # Fail open - allow query if validation fails
            return True, "Validation unavailable"
        
        return False, "Not a botanical query"

    async def get_common_name_only(self, scientific_name: str) -> str:
        """Get only the common name for a plant (lightweight LLM call)"""
        prompt = f"What is the common name for '{scientific_name}'? Answer with ONLY the common name, nothing else."
        
        try:
            res = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a botanical expert. Provide only the common name."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 20,
                },
                timeout=_TIMEOUT,
            )
            
            if res.status_code == 200:
                common_name = res.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                return common_name
        except Exception as exc:
            print(f"[PlantProfiler] Common name error: {exc}")
        
        # Fallback: use first word of scientific name
        return scientific_name.split()[0] if scientific_name else "Unknown"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def get_profile(
        self,
        scientific_name: str,
        family: str = "",
        genus: str = "",
    ) -> dict:
        """
        Return a botanical profile dict for the given plant.
        Results are cached by (scientific_name, family, genus).
        A fallback profile is returned on any API/parse error.
        """
        if scientific_name in ("Unknown Plant", "", None):
            return {}

        if not _is_in_domain_name(scientific_name):
            # Prevent serving or caching obvious non-botanical entries.
            raw_key = f"{scientific_name}|{family}|{genus}"
            canon_key = f"{_canonical_cache_name(scientific_name)}|{family}|{genus}"
            removed = False
            if raw_key in self._cache:
                self._cache.pop(raw_key, None)
                removed = True
            if canon_key in self._cache:
                self._cache.pop(canon_key, None)
                removed = True
            if removed:
                self._save_cache()
            return {}

        raw_cache_key = f"{scientific_name}|{family}|{genus}"
        cache_key = f"{_canonical_cache_name(scientific_name)}|{family}|{genus}"

        # Fast path – cache hit
        if cached := self._cache.get(cache_key):
            print(f"[PlantProfiler] Cache HIT  — {cache_key}")
            return cached

        # Backwards compatibility: check raw key (from older cache versions)
        if cached := self._cache.get(raw_cache_key):
            print(f"[PlantProfiler] Cache HIT (legacy key) — {raw_cache_key}")
            # Also write to canonical key so future lookups are stable.
            self._cache[cache_key] = cached
            self._save_cache()
            return cached

        print(f"[PlantProfiler] Cache MISS — generating profile for {scientific_name}")
        profile = await self._fetch_profile(scientific_name, family, genus)

        # Persist to cache
        self._cache[cache_key] = profile
        self._save_cache()

        return profile

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    async def _fetch_profile(self, name: str, family: str, genus: str) -> dict:
        """Call OpenAI and return a parsed profile dict."""
        user_msg = _USER_MSG_TEMPLATE.format(name=name, family=family, genus=genus)

        try:
            res = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_MSG},
                        {"role": "user", "content": user_msg},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                },
                timeout=_TIMEOUT,
            )
            if res.status_code != 200:
                raise RuntimeError(f"OpenAI HTTP {res.status_code}: {res.text}")

            content = (
                res.json()
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            print("[PlantProfiler] Response received — parsing JSON…")
            parsed = _try_parse_json(content)
            if parsed:
                print(f"[PlantProfiler] Parsed OK: {list(parsed.keys())}")
                return parsed

            # Parsing failed — log and return fallback
            print(f"[PlantProfiler] Parse failed. Raw content snippet:\n{content[:500]}")

        except Exception as exc:
            print(f"[PlantProfiler] API error [{type(exc).__name__}]: {exc}")

        # Build fallback
        fallback = dict(_FALLBACK_PROFILE)
        fallback["common_name"] = name.split()[0]
        fallback["description"] = f"A botanical profile for {name} ({family})."
        fallback["taxonomy"] = f"{family}, {genus}"
        return fallback

    # ------------------------------------------------------------------
    # Cache I/O
    # ------------------------------------------------------------------
    def _load_cache(self) -> None:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception as exc:
                print(f"[PlantProfiler] Could not load cache: {exc}")
                self._cache = {}
        else:
            self._cache = {}

    def _save_cache(self) -> None:
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"[PlantProfiler] Could not save cache: {exc}")

