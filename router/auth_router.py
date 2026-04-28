from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import authorization.index as auth_db
from controller.auth_controller import require_admin_key

router = APIRouter(prefix="/api/auth", tags=["authorization"])


class GenerateKeyRequest(BaseModel):
    app_name: str
    secret_key: str | None = None   # optional — auto-generated if not provided


@router.post("/generate-key", response_model=dict)
async def generate_key(body: GenerateKeyRequest, _: bool = Depends(require_admin_key)):
    """Generate a new API key for the given app name."""
    try:
        key_doc = await auth_db.generate_api_key(body.app_name, body.secret_key)
        return {
            "message": "API key generated successfully",
            "data": key_doc,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating API key: {str(e)}")


@router.get("/keys", response_model=dict)
async def list_keys(_: bool = Depends(require_admin_key)):
    """List all registered API keys (masked)."""
    try:
        keys = await auth_db.list_api_keys()
        return {"message": "API keys retrieved", "data": keys}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing keys: {str(e)}")


@router.patch("/restore-key", response_model=dict)
async def restore_key(api_key: str, _: bool = Depends(require_admin_key)):
    """Re-activate a previously revoked API key."""
    try:
        success = await auth_db.restore_api_key(api_key)
        if not success:
            raise HTTPException(status_code=404, detail="API key not found or already active.")
        return {"message": "API key restored successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error restoring key: {str(e)}")


@router.delete("/revoke-key", response_model=dict)
async def revoke_key(api_key: str, _: bool = Depends(require_admin_key)):
    """Revoke (deactivate) an API key."""
    try:
        success = await auth_db.revoke_api_key(api_key)
        if not success:
            raise HTTPException(status_code=404, detail="API key not found.")
        return {"message": "API key revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error revoking key: {str(e)}")
