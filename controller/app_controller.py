import rembg
from rembg import new_session
from fastapi import HTTPException, UploadFile
from PIL import Image
from io import BytesIO
import asyncio
import config.index as _config
from utils.preprocess_image import read_image, generate_unique_path
from inits.server_init import thread_pool

# Load the model once at import time — avoids reloading on every request
_rembg_session = new_session("u2net")


def _process_image(image: Image.Image, output_path: str) -> str:
    """CPU-bound work: remove background and save. Runs in thread pool."""
    img_bytes = BytesIO()
    image.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    result_bytes = rembg.remove(img_bytes.read(), session=_rembg_session)

    result_image = Image.open(BytesIO(result_bytes))
    result_image.save(output_path, "WEBP")

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
