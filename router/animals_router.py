import logging
import threading

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from controller.auth_controller import require_api_key
from controller.animals_controller import (
    dog_info_search,
    find_insect_image_and_info,
    find_spider_image_and_info,
)
from database.database_config import get_authorization_db
from database import animal_crud

def ensure_absolute_url(url: str) -> str:
    """Ensure the URL is absolute by prepending BASE_URL if it is relative."""
    if not url:
        return url
    url = url.replace('\\', '/')
    if url.startswith("http://") or url.startswith("https://") or url.startswith("data:"):
        return url
    from config.index import BASE_URL
    return f"{BASE_URL.rstrip('/')}/{url.lstrip('/')}"


# ── Semaphore (max 30 concurrent animal-identifier threads) ───────────────────
_semaphore = threading.Semaphore(30)

router = APIRouter(prefix="/api/animals", tags=["animals-identifier"])


# =============================================================================
# DOG BREED IDENTIFIER
# =============================================================================

@router.post("/dog-breed-identifier/search", response_class=JSONResponse)
async def search_dog_info(
    request: Request,
    _auth: dict = Depends(require_api_key)
):
    """
    Identify dog breed(s) and return info + scraped images.

    Body JSON:
        { "labels": ["Golden Retriever", "Labrador"] }
    """
    data = await request.json()
    breeds = data.get('labels', [])

    if not breeds:
        return JSONResponse(status_code=400, content={'error': 'No labels found in request'})

    db = get_authorization_db()
    results = []
    missing_breeds = []

    # Check database cache first
    for breed in breeds:
        cached = await animal_crud.get_animal_profile(db, breed, "dog")
        if cached and cached.get("info"):
            images = [ensure_absolute_url(u) for u in cached.get("images", [])]
            results.append({
                'dog_breed': breed,
                'dog_info': cached["info"],
                'dog_images': images
            })
        else:
            missing_breeds.append(breed)

    # If any breeds are missing from cache, fetch them via background thread
    if missing_breeds:
        return_data: list = []
        additional_data = {'breeds': missing_breeds}

        _semaphore.acquire()
        try:
            t = threading.Thread(
                target=dog_info_search,
                args=(None, additional_data, return_data),
            )
            t.start()
            t.join()
        finally:
            _semaphore.release()

        # Cache newly scraped/generated profiles and append to results
        for item in return_data:
            breed = item.get('dog_breed')
            info = item.get('dog_info', '')
            images = [ensure_absolute_url(u) for u in item.get('dog_images', [])]
            
            # Save to DB only if we actually got info
            if info:
                await animal_crud.create_animal_profile(
                    db=db,
                    name=breed,
                    animal_type="dog",
                    info=info,
                    images=images
                )
            item['dog_images'] = images
            results.append(item)

    if not results:
        return JSONResponse(content={"response": ""})

    return JSONResponse(content=results)


# =============================================================================
# INSECT IDENTIFIER
# =============================================================================

@router.post("/insect-identifier/search", response_class=JSONResponse)
async def find_insect_info(
    request: Request,
    _auth: dict = Depends(require_api_key)
):
    """
    Return info for one or more insect names.

    Body JSON:
        { "labels": ["Monarch Butterfly", "Firefly"] }
    """
    data = await request.json()
    labels = data.get('labels', [])

    if not labels:
        return JSONResponse(status_code=400, content={'error': 'No labels found in request'})

    db = get_authorization_db()
    results = []
    missing_labels = []

    # Check database cache first
    for label in labels:
        cached = await animal_crud.get_animal_profile(db, label, "insect")
        if cached and cached.get("info"):
            results.append({
                'insect_name': label,
                'insect_info': cached["info"]
            })
        else:
            missing_labels.append(label)

    # If any labels are missing from cache, fetch them via background thread
    if missing_labels:
        return_data: list = []
        additional_data = {'labels': missing_labels}

        _semaphore.acquire()
        try:
            t = threading.Thread(
                target=find_insect_image_and_info,
                args=(None, additional_data, return_data),
            )
            t.start()
            t.join()
        finally:
            _semaphore.release()

        # Cache newly generated profiles and append to results
        for item in return_data:
            name = item.get('insect_name')
            info = item.get('insect_info', '')
            images = [ensure_absolute_url(u) for u in item.get('insect_images', [])]
            
            # Save to DB only if we actually got info
            if info:
                await animal_crud.create_animal_profile(
                    db=db,
                    name=name,
                    animal_type="insect",
                    info=info,
                    images=images
                )
            results.append(item)

    if not results:
        return JSONResponse(content={"response": ""})

    return JSONResponse(content=results)


# =============================================================================
# SPIDER IDENTIFIER
# =============================================================================

@router.post("/spider-identifier/search", response_class=JSONResponse)
async def find_spider_info(
    request: Request,
    _auth: dict = Depends(require_api_key)
):
    """
    Return info for one or more spider names.

    Body JSON:
        { "labels": ["Black Widow", "Tarantula"] }
    """
    data = await request.json()
    labels = data.get('labels', [])

    if not labels:
        return JSONResponse(status_code=400, content={'error': 'No labels found in request'})

    db = get_authorization_db()
    results = []
    missing_labels = []

    # Check database cache first
    for label in labels:
        cached = await animal_crud.get_animal_profile(db, label, "spider")
        if cached and cached.get("info"):
            results.append({
                'spider_name': label,
                'spider_info': cached["info"]
            })
        else:
            missing_labels.append(label)

    # If any labels are missing from cache, fetch them via background thread
    if missing_labels:
        return_data: list = []
        additional_data = {'labels': missing_labels}

        _semaphore.acquire()
        try:
            t = threading.Thread(
                target=find_spider_image_and_info,
                args=(None, additional_data, return_data),
            )
            t.start()
            t.join()
        finally:
            _semaphore.release()

        # Cache newly generated profiles and append to results
        for item in return_data:
            name = item.get('spider_name')
            info = item.get('spider_info', '')
            images = [ensure_absolute_url(u) for u in item.get('spider_images', [])]
            
            # Save to DB only if we actually got info
            if info:
                await animal_crud.create_animal_profile(
                    db=db,
                    name=name,
                    animal_type="spider",
                    info=info,
                    images=images
                )
            results.append(item)

    if not results:
        return JSONResponse(content={"response": ""})

    return JSONResponse(content=results)
