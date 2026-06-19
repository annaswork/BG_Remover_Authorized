from fastapi import APIRouter, UploadFile, File, Depends, Request
from fastapi import HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from controller.app_controller import remove_background
from controller.auth_controller import require_api_key
from utils.session import verify_session_token, COOKIE_NAME
import os, shutil
import config.index as _config

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/api/bg-remover", tags=["bg-remover"])
page_router = APIRouter(tags=["pages"])


@router.get("/", response_model=dict)
async def read_root():
    return {"message": "BG Remover API is running"}


@page_router.get("/login", response_class=HTMLResponse)
async def serve_login(request: Request):
    """Public login page — redirect to dashboard if already authenticated."""
    token = request.cookies.get(COOKIE_NAME)
    if verify_session_token(token):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        headers={"content-type": "text/html; charset=utf-8"},
    )


@page_router.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    """Dashboard — redirect to login if session is missing or expired."""
    token = request.cookies.get(COOKIE_NAME)
    if not verify_session_token(token):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        headers={"content-type": "text/html; charset=utf-8"},
    )


@router.post("/remove", response_model=dict)
async def remove_bg(
    file: UploadFile = File(..., description="Image file to process"),
    _auth: dict = Depends(require_api_key),
):
    """
    Remove the background from an uploaded image.
    Requires a valid API key in the **X-API-Key** header.
    """
    return await remove_background(file)


@router.delete("/clear-results", response_model=dict)
async def clear_results():
    """
    Delete all files inside static/results to free up disk space.
    """
    results_dir = _config.IMAGE_PATH

    if not os.path.exists(results_dir):
        raise HTTPException(status_code=404, detail="Results directory not found.")

    deleted = 0
    errors = []

    for filename in os.listdir(results_dir):
        file_path = os.path.join(results_dir, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                deleted += 1
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                deleted += 1
        except Exception as e:
            errors.append({"file": filename, "error": str(e)})

    return {
        "message": f"Cleared {deleted} item(s) from results folder.",
        "deleted": deleted,
        "errors": errors,
    }
