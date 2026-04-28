from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
import authorization.index as auth_db
from config.index import ADMIN_API_KEY

# Header scheme — clients send: X-API-Key: <key>
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def require_api_key(api_key: str = Security(api_key_header)) -> dict:
    """FastAPI dependency that enforces API key authentication."""
    if not api_key:
        raise HTTPException(status_code=401, detail="API key missing. Provide it via the X-API-Key header.")

    key_doc = await auth_db.validate_api_key(api_key)
    if not key_doc:
        raise HTTPException(status_code=403, detail="Invalid or inactive API key.")

    return key_doc


async def require_admin_key(admin_key: str = Security(admin_key_header)) -> bool:
    """FastAPI dependency that enforces Admin key authentication."""
    if not admin_key:
        raise HTTPException(status_code=401, detail="Admin key missing. Provide it via the X-Admin-Key header.")

    if admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key.")

    return True
