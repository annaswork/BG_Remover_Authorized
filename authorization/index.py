import hmac
import hashlib
import secrets
from typing import Optional
from database.database_funcs import get_authorization_db
from database.authorization_model import APIKey
from config.index import AUTHORIZATION_COLLECTION_NAME, SECRET_KEY


def _sign_key(raw_key: str) -> str:
    """Combine raw_key with SECRET_KEY using HMAC-SHA256, return hex digest."""
    return hmac.new(
        SECRET_KEY.encode(),
        raw_key.encode(),
        hashlib.sha256
    ).hexdigest()


async def generate_api_key(app_name: str, secret_key: str = None) -> dict:
    """Generate a new API key for the given app name.
    
    If secret_key is provided it is used as the base, otherwise a random
    token is generated. Either way the final stored key is HMAC-signed
    with the server SECRET_KEY from .env.
    """
    db = get_authorization_db()
    collection = db[AUTHORIZATION_COLLECTION_NAME]

    base = secret_key if secret_key else secrets.token_urlsafe(32)
    signed_key = _sign_key(base)

    # Reject duplicates
    existing = await collection.find_one({"api_key": signed_key})
    if existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="This key already exists. Choose a different secret.")

    key_doc = APIKey(app_name=app_name, api_key=signed_key)
    key_dict = key_doc.model_dump(exclude={"id"})

    result = await collection.insert_one(key_dict)
    created = await collection.find_one({"_id": result.inserted_id})
    if created:
        created["_id"] = str(created["_id"])

    return created


async def validate_api_key(api_key: str) -> Optional[dict]:
    """Return the key document if valid and active, else None."""
    db = get_authorization_db()
    collection = db[AUTHORIZATION_COLLECTION_NAME]

    doc = await collection.find_one({"api_key": api_key, "is_active": True})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def list_api_keys() -> list:
    """List all API keys (without exposing the raw key value)."""
    db = get_authorization_db()
    collection = db[AUTHORIZATION_COLLECTION_NAME]

    keys = []
    async for doc in collection.find({}):
        doc["_id"] = str(doc["_id"])
        doc["api_key"] = doc["api_key"]
        keys.append(doc)
    return keys


async def revoke_api_key(api_key: str) -> bool:
    """Deactivate an API key."""
    db = get_authorization_db()
    collection = db[AUTHORIZATION_COLLECTION_NAME]

    result = await collection.update_one(
        {"api_key": api_key},
        {"$set": {"is_active": False}}
    )
    return result.modified_count > 0


async def restore_api_key(api_key: str) -> bool:
    """Re-activate a previously revoked API key."""
    db = get_authorization_db()
    collection = db[AUTHORIZATION_COLLECTION_NAME]

    result = await collection.update_one(
        {"api_key": api_key},
        {"$set": {"is_active": True}}
    )
    return result.modified_count > 0
