import os
import rembg
from rembg import new_session
from fastapi import HTTPException, UploadFile
from PIL import Image
from io import BytesIO
import asyncio
import numpy as np
import cv2
import config.index as _config
from utils.preprocess_image import read_image, generate_unique_path
from inits.server_init import thread_pool

# Load the model once at import time — avoids reloading on every request
_rembg_session = new_session("u2net")


def _process_image(image: Image.Image, output_path: str) -> str:
    """CPU-bound work: remove background and save as WEBP. Runs in thread pool."""
    img_bytes = BytesIO()
    image.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    result_bytes = rembg.remove(img_bytes.read(), session=_rembg_session)

    result_image = Image.open(BytesIO(result_bytes))

    # Ensure RGBA mode to preserve transparency
    if result_image.mode != "RGBA":
        result_image = result_image.convert("RGBA")

    # Use OpenCV to save as WEBP — works regardless of Pillow's libwebp support
    # PIL RGBA → numpy → cv2 BGRA (OpenCV uses BGR channel order)
    img_array = np.array(result_image)                        # H x W x 4, RGBA
    img_bgra  = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGRA)  # BGRA for OpenCV
    cv2.imwrite(output_path, img_bgra, [cv2.IMWRITE_WEBP_QUALITY, 90])

    return output_path


async def remove_background(file: UploadFile) -> dict:
    """Read an uploaded image, remove its background, save as WebP, return URL."""
    try:
        image: Image.Image = await read_image(file)

        output_filename = generate_unique_path(file.filename or "image.png")
        output_path = f"{_config.IMAGE_PATH}{output_filename}"

        # Offload CPU-heavy work to thread pool — keeps event loop free
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(thread_pool, _process_image, image, output_path)

        image_url = f"{_config.IMAGE_URL_PREFIX}results/{output_filename}"

        return {
            "message": "Background removed successfully",
            "image_url": image_url,
            "filename": output_filename,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Background removal failed: {str(e)}")


def clear_static_subfolders() -> dict:
    """
    Delete every file inside each direct subfolder of STATIC_DIR.
    Subdirectory structure is preserved — only files are removed.
    Operations are strictly confined to absolute paths inside STATIC_DIR.
    """
    static_dir = os.path.abspath(_config.STATIC_DIR)

    if not os.path.isdir(static_dir):
        raise HTTPException(status_code=404, detail="Static directory not found.")

    deleted = 0
    errors = []

    for entry in os.scandir(static_dir):
        if not entry.is_dir(follow_symlinks=False):
            continue  # skip loose files at the top level of static/

        subfolder = os.path.abspath(entry.path)

        # Safety guard: ensure we never stray outside STATIC_DIR
        if not subfolder.startswith(static_dir + os.sep):
            continue

        for file_entry in os.scandir(subfolder):
            if not file_entry.is_file(follow_symlinks=False):
                continue  # leave any nested subdirectories untouched
            try:
                os.remove(file_entry.path)
                deleted += 1
            except Exception as e:
                errors.append({"file": file_entry.path, "error": str(e)})

    return {"deleted": deleted, "errors": errors}
