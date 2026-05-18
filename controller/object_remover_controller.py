"""
object_remover_controller.py
-----------------------------
Embedded object-removal controller for OZI_ANALYTICS.

LaMa (inpainting) and SAM (segmentation) are loaded once at startup
via inits/models_init.py — exactly like face_model and swapper.
All CPU-heavy work runs in the shared thread_pool from server_init.py
to keep the async event loop free.
"""

import os
import uuid
import json
import asyncio
import base64
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from fastapi import HTTPException, UploadFile, status, Request

import config.index as _config
from inits.server_init import thread_pool
from inits.models_init import lama_model, sam_processor

from iopaint.schema import InpaintRequest
from iopaint.helper import decode_base64_to_image, concat_alpha_channel, load_img


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _results_dir() -> Path:
    """Return (and create if needed) the directory where results are saved."""
    path = Path(_config.OBJECT_REMOVER_RESULTS_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_webp(pil_image: Image.Image) -> str:
    """Save a PIL image as WebP into the results dir. Returns the filename."""
    filename = f"{uuid.uuid4().hex}.webp"
    pil_image.save(_results_dir() / filename, format="WEBP", quality=90)
    return filename


def _result_url(request: Request, filename: str) -> str:
    """Build a full absolute URL for a saved result file."""
    base = str(request.base_url).rstrip("/")
    return f"{base}{_config.OBJECT_REMOVER_URL_PREFIX}/{filename}"


def _check_lama():
    """Raise 503 early if LaMa was not enabled / failed to load."""
    if lama_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "LaMa inpainting model is not loaded. "
                "Set LAMA_ENABLE=true in .env and restart the server."
            ),
        )


def _check_sam():
    """Raise 503 early if SAM was not enabled / failed to load."""
    if sam_processor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "SAM segmentation model is not loaded. "
                "Set SAM_ENABLE=true in .env and restart the server."
            ),
        )


# ---------------------------------------------------------------------------
# Sync workers (run inside thread_pool)
# ---------------------------------------------------------------------------

def _run_inpaint(
    np_image: np.ndarray,
    np_mask: np.ndarray,
    alpha_channel,
    ldmSteps: int,
    hdStrategy: str,
    hdStrategyCropMargin: int,
    hdStrategyCropTrigerSize: int,
    hdStrategyResizeLimit: int,
    maskExpand: int,
) -> str:
    """
    CPU/GPU-bound: expand mask → run LaMa → save result.
    Returns saved filename only — URL is built on the async side
    where the Request object is available.
    """
    if maskExpand > 0:
        kernel = np.ones((maskExpand, maskExpand), np.uint8)
        np_mask = cv2.dilate(np_mask, kernel, iterations=1)

    if np_image.shape[:2] != np_mask.shape[:2]:
        raise ValueError(
            f"Image size {np_image.shape[:2]} and mask size {np_mask.shape[:2]} don't match."
        )

    inpaint_req = InpaintRequest(
        ldmSteps=ldmSteps,
        hdStrategy=hdStrategy,
        hdStrategyCropMargin=hdStrategyCropMargin,
        hdStrategyCropTrigerSize=hdStrategyCropTrigerSize,
        hdStrategyResizeLimit=hdStrategyResizeLimit,
    )

    print(f"[object_remover] Inpainting {np_image.shape[:2]}...")
    rgb_np_img = lama_model(np_image, np_mask, inpaint_req)
    print("[object_remover] Inpainting complete.")

    rgb_np_img = cv2.cvtColor(rgb_np_img.astype(np.uint8), cv2.COLOR_BGR2RGB)
    rgb_res    = concat_alpha_channel(rgb_np_img, alpha_channel)
    return _save_webp(Image.fromarray(rgb_res))


def _run_sam(image_rgb: np.ndarray, points: list, labels: list) -> str:
    """
    CPU/GPU-bound: run SAM segmentation → return base64-encoded PNG mask.
    """
    print(f"[object_remover] SAM — {len(points)} point(s)")
    mask = sam_processor.generate_mask(image_rgb, points, labels)
    _, buffer = cv2.imencode(".png", mask)
    return base64.b64encode(buffer).decode("utf-8")


# ---------------------------------------------------------------------------
# Public async functions (called by the router)
# ---------------------------------------------------------------------------

async def health() -> dict:
    """Return load status of both models."""
    return {
        "status": "ok",
        "lama_loaded": lama_model is not None,
        "sam_loaded":  sam_processor is not None,
    }


async def inpaint_base64(body: dict, request: Request) -> dict:
    """
    Remove an object using base64-encoded image + mask (JSON body).

    Required keys:
      image  : base64 string — source image
      mask   : base64 string — B&W PNG (white = erase, black = keep)

    Optional keys (all have defaults):
      ldmSteps, hdStrategy, hdStrategyCropMargin,
      hdStrategyCropTrigerSize, hdStrategyResizeLimit, maskExpand
    """
    _check_lama()

    if "image" not in body or "mask" not in body:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request body must contain 'image' and 'mask' base64 fields.",
        )

    try:
        np_image, alpha_channel, _, _ = decode_base64_to_image(body["image"])
        np_mask,  _,             _, _ = decode_base64_to_image(body["mask"], gray=True)
        np_mask = cv2.threshold(np_mask, 127, 255, cv2.THRESH_BINARY)[1]

        loop     = asyncio.get_event_loop()
        filename = await loop.run_in_executor(
            thread_pool, _run_inpaint,
            np_image, np_mask, alpha_channel,
            int(body.get("ldmSteps",                25)),
            str(body.get("hdStrategy",              "Original")),
            int(body.get("hdStrategyCropMargin",    128)),
            int(body.get("hdStrategyCropTrigerSize", 800)),
            int(body.get("hdStrategyResizeLimit",   2048)),
            int(body.get("maskExpand",              10)),
        )

        return {
            "message":    "Object removed successfully",
            "result_url": _result_url(request, filename),
            "filename":   filename,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


async def inpaint_file(
    image: UploadFile,
    mask: UploadFile,
    request: Request,
    ldmSteps: int = 25,
    hdStrategy: str = "Original",
    hdStrategyCropMargin: int = 128,
    hdStrategyCropTrigerSize: int = 800,
    hdStrategyResizeLimit: int = 2048,
    maskExpand: int = 10,
) -> dict:
    """
    Remove an object using uploaded image + mask files (multipart/form-data).
    """
    _check_lama()

    try:
        image_bytes = await image.read()
        mask_bytes  = await mask.read()

        np_image, alpha_channel, _ = load_img(image_bytes, return_info=True)
        np_mask,  _                = load_img(mask_bytes, gray=True)
        np_mask = cv2.threshold(np_mask, 127, 255, cv2.THRESH_BINARY)[1]

        loop     = asyncio.get_event_loop()
        filename = await loop.run_in_executor(
            thread_pool, _run_inpaint,
            np_image, np_mask, alpha_channel,
            ldmSteps, hdStrategy,
            hdStrategyCropMargin, hdStrategyCropTrigerSize,
            hdStrategyResizeLimit, maskExpand,
        )

        return {
            "message":    "Object removed successfully",
            "result_url": _result_url(request, filename),
            "filename":   filename,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


async def sam_segment(image: UploadFile, points: str) -> dict:
    """
    Run SAM on the uploaded image using click-point coordinates.

    points: JSON string e.g. '[{"x": 213, "y": 232}]'
    Returns: {"mask": "<base64-encoded PNG>"}
    """
    _check_sam()

    try:
        point_objects = json.loads(points)
        parsed_points = [[p["x"], p["y"]] for p in point_objects]
        parsed_labels = [1] * len(parsed_points)   # all foreground clicks

        image_bytes = await image.read()
        np_arr      = np.frombuffer(image_bytes, np.uint8)
        img         = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        img_rgb     = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        loop     = asyncio.get_event_loop()
        mask_b64 = await loop.run_in_executor(
            thread_pool, _run_sam,
            img_rgb, parsed_points, parsed_labels,
        )

        return {"mask": mask_b64}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


async def clear_results() -> dict:
    """Delete all saved result images from the object remover results folder."""
    try:
        deleted, errors = 0, []
        for f in _results_dir().iterdir():
            try:
                if f.is_file():
                    f.unlink()
                    deleted += 1
            except Exception as e:
                errors.append({"file": f.name, "error": str(e)})

        return {
            "message": f"Cleared {deleted} file(s) from object remover results.",
            "deleted": deleted,
            "errors":  errors,
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))