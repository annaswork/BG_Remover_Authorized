from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
import authorization.index as auth_db
from controller.auth_controller import require_admin_session
from config.index import ADMIN_USERNAME, ADMIN_PASSWORD
from utils.session import create_session_token, COOKIE_NAME

router = APIRouter(prefix="/api/auth", tags=["authorization"])


# ── Pydantic models ───────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class GenerateKeyRequest(BaseModel):
    app_name: str
    secret_key: str | None = None   # optional — auto-generated if omitted


# ── Session login / logout ────────────────────────────────────────────────────

@router.post("/login", response_model=dict)
async def login(body: LoginRequest, response: Response):
    """
    Authenticate with ADMIN_USERNAME / ADMIN_PASSWORD from .env.
    Issues an HTTP-only signed session cookie on success.
    """
    if body.username != ADMIN_USERNAME or body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = create_session_token(body.username)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        # Session cookie (no max_age) — cleared on browser close / page refresh
        # secure=True,  # uncomment when serving over HTTPS
    )
    return {"message": "Login successful", "username": body.username}


@router.post("/logout", response_model=dict)
async def logout(response: Response):
    """Clear the session cookie."""
    response.delete_cookie(COOKIE_NAME, samesite="lax")
    return {"message": "Logged out."}


@router.get("/me", response_model=dict)
async def me(username: str = Depends(require_admin_session)):
    """Return the currently authenticated admin username (session check)."""
    return {"username": username}


# ── Key management (now protected by session cookie) ─────────────────────────

@router.post("/generate-key", response_model=dict)
async def generate_key(
    body: GenerateKeyRequest,
    _: str = Depends(require_admin_session),
):
    """Generate a new API key for the given app name."""
    try:
        key_doc = await auth_db.generate_api_key(body.app_name, body.secret_key)
        return {"message": "API key generated successfully", "data": key_doc}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating API key: {e}")


@router.get("/keys", response_model=dict)
async def list_keys(_: str = Depends(require_admin_session)):
    """List all registered API keys."""
    try:
        keys = await auth_db.list_api_keys()
        return {"message": "API keys retrieved", "data": keys}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing keys: {e}")


@router.patch("/restore-key", response_model=dict)
async def restore_key(api_key: str, _: str = Depends(require_admin_session)):
    """Re-activate a previously revoked API key."""
    try:
        success = await auth_db.restore_api_key(api_key)
        if not success:
            raise HTTPException(status_code=404, detail="API key not found or already active.")
        return {"message": "API key restored successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error restoring key: {e}")


@router.delete("/revoke-key", response_model=dict)
async def revoke_key(api_key: str, _: str = Depends(require_admin_session)):
    """Revoke (deactivate) an API key."""
    try:
        success = await auth_db.revoke_api_key(api_key)
        if not success:
            raise HTTPException(status_code=404, detail="API key not found.")
        return {"message": "API key revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error revoking key: {e}")


@router.delete("/delete-key", response_model=dict)
async def delete_key(api_key: str, _: str = Depends(require_admin_session)):
    """Permanently delete an API key."""
    try:
        success = await auth_db.delete_api_key(api_key)
        if not success:
            raise HTTPException(status_code=404, detail="API key not found.")
        return {"message": "API key deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting key: {e}")
