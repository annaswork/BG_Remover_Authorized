from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader
import authorization.index as auth_db
from config.index import ADMIN_API_KEY
from utils.session import verify_session_token, COOKIE_NAME

# ── Header scheme for API consumers ──────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# ── Legacy X-Admin-Key header (kept for Swagger / programmatic access) ────────
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def require_api_key(api_key: str = Security(api_key_header)) -> dict:
    """FastAPI dependency: enforces API key authentication."""
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key missing. Provide it via the X-API-Key header.",
        )
    key_doc = await auth_db.validate_api_key(api_key)
    if not key_doc:
        raise HTTPException(status_code=403, detail="Invalid or inactive API key.")
    return key_doc


async def require_admin_key(admin_key: str = Security(admin_key_header)) -> bool:
    """FastAPI dependency: enforces Admin key authentication (legacy header)."""
    if not admin_key:
        raise HTTPException(
            status_code=401,
            detail="Admin key missing. Provide it via the X-Admin-Key header.",
        )
    if admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key.")
    return True


async def require_admin_session(request: Request) -> str:
    """
    FastAPI dependency: validates the HTTP-only session cookie set by
    POST /api/auth/login.  Raises 401 if the cookie is absent or invalid.
    Returns the authenticated username on success.
    """
    token = request.cookies.get(COOKIE_NAME)
    username = verify_session_token(token) if token else None
    if not username:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please log in at /login.",
        )
    return username
