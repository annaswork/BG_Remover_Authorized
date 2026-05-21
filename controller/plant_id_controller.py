from fastapi import HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
import asyncio
from inits.server_init import thread_pool, driver
from inits.models_init import (
    bioclip_model,
    bioclip_preprocess,
    faiss_index,
    plant_metadata,
    plant_profiler,
)
from PIL import Image, ImageOps
import io
import torch
import numpy as np
import cv2
from database.database_config import get_authorization_db
from database import plant_crud
import re

from utils.image_scraper import scrape_thumbnails, download_thumbnails
from config.index import BASE_URL

try:
    from bson import ObjectId
except Exception:  # pragma: no cover - fallback when bson is unavailable
    ObjectId = None

_DOMAIN_ERROR = "This API only returns information about plants, vegetables, fruits, and fungi."
_NAME_INDEX: dict[str, str] | None = None

def _json_safe(value):
    if ObjectId is None:
        return jsonable_encoder(value)
    return jsonable_encoder(value, custom_encoder={ObjectId: str})


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _build_name_index() -> dict[str, str]:
    """
    Build a lightweight lookup of known botanical names from plant_metadata.
    Keys are normalized names, values are a representative display name.
    """
    index: dict[str, str] = {}
    meta = plant_metadata
    if not meta:
        return index

    def _add(name: str | None):
        if not name:
            return
        k = _norm(name)
        if not k:
            return
        index.setdefault(k, name.strip())

    try:
        if isinstance(meta, list):
            for item in meta:
                if isinstance(item, str):
                    _add(item)
                    continue
                if not isinstance(item, dict):
                    continue
                _add(item.get("scientificName"))
                _add(item.get("scientific_name"))
                _add(item.get("commonName"))
                _add(item.get("common_name"))
                _add(item.get("name"))
                # Some datasets store concatenated taxonomy strings
                _add(item.get("genus"))
        elif isinstance(meta, dict):
            for _, item in meta.items():
                if isinstance(item, str):
                    _add(item)
                    continue
                if not isinstance(item, dict):
                    continue
                _add(item.get("scientificName"))
                _add(item.get("scientific_name"))
                _add(item.get("commonName"))
                _add(item.get("common_name"))
                _add(item.get("name"))
                _add(item.get("genus"))
    except Exception:
        # If metadata is malformed, fail closed by returning an empty index.
        return {}

    return index


def _looks_like_latin_binomial(name: str) -> bool:
    # e.g., "Solanum tuberosum" or "Agaricus bisporus"
    s = (name or "").strip()
    return bool(re.match(r"^[A-Z][a-z]+(?:\s+[a-z][a-z-]+){1,3}$", s))


def _is_allowed_domain_query(name: str) -> tuple[bool, str | None, str]:
    """
    Decide if a query is in-domain (plants/veggies/fruits/fungi).
    Returns (allowed, suggestion, reason).
    """
    q = _norm(name)
    if not q:
        return False, None, "Empty query"

    # Fast reject for obvious non-botanical categories
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
        "man",
        "woman",
        "boy",
        "girl",
        "car",
        "phone",
        "laptop",
        "chair",
        "table",
    }
    if q in banned:
        return False, None, f"'{name.strip()}' is not a plant/fruit/vegetable/fungus"

    # Always allow clear fungi keywords even if not present in plant metadata
    fungi_keywords = ("fungus", "fungi", "mushroom", "toadstool", "yeast", "mold", "mould")
    if any(k in q for k in fungi_keywords):
        return True, None, "Fungi keyword"

    global _NAME_INDEX
    if _NAME_INDEX is None:
        _NAME_INDEX = _build_name_index()

    # If we have metadata, validate strictly against it (fast hash lookup)
    if _NAME_INDEX:
        if q in _NAME_INDEX:
            return True, None, "Known botanical name"

        # Try a few cheap normalizations that users commonly type
        q2 = re.sub(r"[^a-z0-9\s-]", "", q)
        if q2 and q2 in _NAME_INDEX:
            return True, None, "Known botanical name"

        # Suggest a close substring match (bounded effort)
        suggestion = None
        prefix_match = None
        if len(q) >= 3:
            # Prefer prefix match, then substring match
            for k, display in _NAME_INDEX.items():
                if k.startswith(q):
                    prefix_match = display
                    break
            if prefix_match:
                suggestion = prefix_match
            else:
                for k, display in _NAME_INDEX.items():
                    if q in k:
                        suggestion = display
                        break

        # If we can't find it in our dataset, we still allow it to go to the LLM.
        # The LLM + backend post-check will reject non-plants by returning {}.
        if _looks_like_latin_binomial(name):
            return True, suggestion, "Scientific-name (not in dataset); using LLM gate"

        return True, suggestion, "Common name (not in dataset); using LLM gate"

    # If we don't have metadata loaded, allow only latin-like scientific names
    # (fail closed otherwise) so we don't spam the LLM with unrelated requests.
    if _looks_like_latin_binomial(name):
        return True, None, "Looks like scientific name"

    return False, None, "No botanical metadata loaded; query doesn't look like a scientific name"

def _bytes_to_pil(image_bytes: bytes) -> Image.Image:
    """
    Convert raw image bytes to a PIL RGB Image.
    Tries PIL first (handles EXIF orientation), falls back to OpenCV
    which is more tolerant of non-standard headers and progressive JPEGs.
    """
    # --- Attempt 1: PIL with EXIF correction ---
    try:
        stream = io.BytesIO(image_bytes)
        img = Image.open(stream)
        img = ImageOps.exif_transpose(img)   # fix rotated photos from phones
        return img.convert("RGB")
    except Exception as pil_err:
        print(f"[_bytes_to_pil] PIL failed (len={len(image_bytes)}, header={image_bytes[:16].hex()}): {pil_err}")
        pass  # fall through to OpenCV

    # --- Attempt 2: OpenCV (handles more formats / corrupt headers) ---
    try:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError("cv2.imdecode returned None — unrecognised format")
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
    except Exception as cv_err:
        raise ValueError(
            f"PIL failed and OpenCV fallback also failed.\n"
            f"  PIL error : {pil_err}\n"
            f"  OpenCV error: {cv_err}"
        )


def _encode_image_sync(image_bytes: bytes) -> np.ndarray:
    """
    Synchronous worker to encode an image using BioCLIP.
    Runs in the thread pool to avoid blocking the FastAPI event loop.
    """
    if bioclip_model is None or bioclip_preprocess is None:
        raise HTTPException(status_code=503, detail="BioCLIP model not loaded")

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image data received")

    try:
        image = _bytes_to_pil(image_bytes)

        # Preprocess image
        image_tensor = bioclip_preprocess(image).unsqueeze(0)

        # Encode image to get embedding
        with torch.no_grad():
            image_features = bioclip_model.encode_image(image_tensor)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        # Convert to numpy
        embedding = image_features.cpu().numpy().astype('float32')
        return embedding
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not process image: {str(e)}. "
                   "Please upload a valid image (JPEG, PNG, WEBP, etc.)."
        )

async def predict_plant(file: UploadFile, top_k: int = 1) -> dict:
    """
    Identify a plant from an uploaded image using local BioCLIP + FAISS.
    Returns only basic info (scientific name, common name) initially.
    Full profile is fetched separately via get_more_info endpoint.
    
    Args:
        file: Uploaded image file
        top_k: Number of top results to return (default: 1)
        
    Returns:
        dict: Basic plant identification with scientific_name and common_name
    """
    if faiss_index is None:
        raise HTTPException(status_code=503, detail="FAISS index not loaded")
    
    # Read image bytes
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="No image data received. Make sure the file field is named 'file' and contains a valid image."
        )

    # Reject obviously non-image content types early
    content_type = (file.content_type or "").lower()
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{content_type}'. Please upload an image (JPEG, PNG, WEBP, etc.)."
        )

    # Encode image in thread pool
    loop = asyncio.get_event_loop()
    query_vector = await loop.run_in_executor(thread_pool, _encode_image_sync, file_bytes)
    
    # Search FAISS index - always get top 1
    distances, indices = faiss_index.search(query_vector, 1)
    
    # Build result for top 1 match
    idx = int(indices[0][0])
    distance = float(distances[0][0])
    
    # Get plant info from metadata
    scientific_name = f"Plant_{idx}"
    family = ""
    genus = ""
    
    if plant_metadata is not None and isinstance(plant_metadata, list):
        if 0 <= idx < len(plant_metadata):
            plant_info = plant_metadata[idx]
            if isinstance(plant_info, dict):
                scientific_name = (plant_info.get("scientificName") or 
                                 plant_info.get("scientific_name") or 
                                 scientific_name)
                family = plant_info.get("family", "")
                genus = plant_info.get("genus", "")
    
    # Check MongoDB first
    db = get_authorization_db()
    existing_plant = await plant_crud.get_plant_by_scientific_name(db, scientific_name)
    
    if existing_plant:
        # Plant exists in DB - return cached data
        print(f"[Predict] Found in DB: {scientific_name}")
        common_name = existing_plant.get("common_name", scientific_name.split()[0])
        image_urls = existing_plant.get("image_urls", [])
        img_avail = existing_plant.get("img_avail", False)
    else:
        # Plant not in DB - get common name from LLM
        print(f"[Predict] Not in DB, calling LLM for common name: {scientific_name}")
        
        if plant_profiler:
            common_name = await plant_profiler.get_common_name_only(scientific_name)
        else:
            common_name = scientific_name.split()[0]
        

        # Save basic info to MongoDB
        await plant_crud.create_plant_basic(
            db=db,
            scientific_name=scientific_name,
            common_name=common_name,
            family=family,
            genus=genus
        )
        print(f"[Predict] Saved basic info to DB: {scientific_name}")
        image_urls = []
        img_avail = False
    
    result = {
        "rank": 1,
        "index": idx,
        "distance": distance,
        "similarity": float(1.0 / (1.0 + distance)),
        "scientific_name": scientific_name,
        "common_name": common_name,
        "family": family,
        "genus": genus,
        "has_full_info": existing_plant.get("all_info", False) if existing_plant else False,
        "image_urls": image_urls,
        "img_avail": img_avail
    }
    
    return {
        "message": "Plant identification completed",
        "results": [result],
        "top_match": result,   # convenience alias used by the frontend
    }

async def get_more_info(scientific_name: str) -> dict:
    """
    Get full plant profile information.
    Checks MongoDB first, calls LLM if not found, then caches result.
    
    Args:
        scientific_name: Scientific name of the plant
        
    Returns:
        dict: Full plant profile
    """
    if not plant_profiler:
        raise HTTPException(
            status_code=503,
            detail="Plant profile generation is not available. OpenAI API key not configured."
        )
    
    # Check MongoDB first
    db = get_authorization_db()
    existing_plant = await plant_crud.get_plant_by_scientific_name(db, scientific_name)
    
    if existing_plant and existing_plant.get("all_info"):
        # Full info already in DB
        print(f"[GetMoreInfo] Found full info in DB: {scientific_name}")
        return {
            "message": "Plant profile retrieved from database",
            "data": _json_safe(existing_plant),
            "source": "database"
        }
    
    # Not in DB or only basic info - call LLM
    print(f"[GetMoreInfo] Calling LLM for full profile: {scientific_name}")
    
    family = existing_plant.get("family", "") if existing_plant else ""
    genus = existing_plant.get("genus", "") if existing_plant else ""
    
    # Get full profile from LLM
    profile = await plant_profiler.get_profile(
        scientific_name=scientific_name,
        family=family,
        genus=genus
    )
    
    # Save to MongoDB
    common_name = profile.get("common_name", scientific_name.split()[0])
    await plant_crud.upsert_plant_full_info(
        db=db,
        scientific_name=scientific_name,
        common_name=common_name,
        profile_data=profile,
        family=family,
        genus=genus
    )
    print(f"[GetMoreInfo] Saved full info to DB: {scientific_name}")
    
    return {
        "message": "Plant profile generated and cached",
        "data": profile,
        "source": "llm"
    }

async def search_plant(query_params: dict) -> dict:
    """
    Search for plant information by name.
    Validates query is botanical, checks MongoDB, calls LLM if needed.
    
    Args:
        query_params: Query parameters (should contain 'scientific_name' or 'name')
        
    Returns:
        dict: Full plant profile information
    """
    if plant_profiler is None:
        raise HTTPException(
            status_code=503, 
            detail="Plant profile generation is not available. OpenAI API key not configured."
        )
    
    scientific_name = query_params.get("scientific_name") or query_params.get("name")
    
    if not scientific_name:
        raise HTTPException(status_code=400, detail="Missing 'scientific_name' or 'name' parameter")
    
    target_name = scientific_name.strip()
    print(f"[Search] Query: '{target_name}'")

    validate_raw = str(query_params.get("validate", "true")).lower()
    validate = validate_raw not in ("0", "false", "no", "off")

    if validate:
        allowed, suggestion, reason = _is_allowed_domain_query(target_name)
        if not allowed:
            return {
                "message": "Rejected",
                "query": target_name,
                "data": {},
                "is_botanical": False,
                "error": _DOMAIN_ERROR,
                "reason": reason,
                "suggestion": suggestion,
            }
    
    # Check MongoDB first (try both scientific and common name)
    db = get_authorization_db()
    existing_plant = await plant_crud.get_plant_by_scientific_name(db, target_name)
    
    if not existing_plant:
        existing_plant = await plant_crud.get_plant_by_common_name(db, target_name)
    
    if existing_plant and existing_plant.get("all_info"):
        # Full info already in DB
        print(f"[Search] Found full info in DB: {target_name}")
        return {
            "message": "Plant profile retrieved from database",
            "query": target_name,
            "data": _json_safe(existing_plant),
            "source": "database",
            "is_botanical": True
        }
    
    # Not in DB or only basic info - call LLM
    print(f"[Search] Calling LLM for full profile: {target_name}")
    
    # Extract optional taxonomy parameters
    family = query_params.get('family', '')
    genus = query_params.get('genus', '')
    
    # Generate plant profile using LLM
    profile = await plant_profiler.get_profile(
        scientific_name=target_name,
        family=family,
        genus=genus
    )

    # If the LLM/generator rejects the request it returns {}.
    if not isinstance(profile, dict) or not profile or profile == {}:
        return {
            "message": "Rejected",
            "query": target_name,
            "data": {},
            "is_botanical": False,
            "error": _DOMAIN_ERROR,
            "reason": "LLM rejected non-botanical query",
        }
    
    # Save to MongoDB
    common_name = profile.get("common_name", target_name.split()[0])

    #Thumbnails scraped for required plant
    urls = scrape_thumbnails(driver,common_name + " plant")
    image_urls = download_thumbnails(urls, common_name, base_url=BASE_URL)

    profile['image_urls'] = image_urls
    profile['img_avail'] = True

    await plant_crud.upsert_plant_full_info(db=db, scientific_name=target_name, common_name=common_name, profile_data=profile, family=family, genus=genus)
    print(f"[Search] Saved full info to DB: {target_name}")
    
    return {
        "message": "Plant profile generated and cached",
        "query": target_name,
        "data": profile,
        "source": "llm",
        "is_botanical": True
    }


