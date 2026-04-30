import os
from io import BytesIO
import asyncio
import time

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile, status
from PIL import Image
import rembg
from rembg import new_session

import config.index as _config
from inits.server_init import thread_pool
from inits.models_init import face_model, swapper, gfpgan_model
from utils.preprocess_image import read_image, convert_to_cv2Image, generate_unique_path
from utils.postprocess_image import save_img_with_url


# Load the background-removal session once (CPU model can be heavy to create repeatedly)
_rembg_session = new_session("u2net")


def detect_face_and_crop_image(image, width, height, unit, dpi, filename, model):
    """
    Synchronous worker:
    - Detect exactly one face using InsightFace
    - Crop around the face with padding
    - Resize/crop to target dimensions
    - Remove background from the cropped face and save as WEBP
    """
    try:
        faces = model.get(image)

        if not faces:
            raise ValueError("No faces detected.")
        if len(faces) > 1:
            raise ValueError("More than one face detected. Please upload an image with exactly one face.")

        # Extract bounding box coordinates
        (x1, y1, x2, y2) = faces[0].bbox.astype(int)

        # Step 1: crop with face-centered padding
        face_w = x2 - x1
        face_h = y2 - y1

        # Padding around detected face box (tuned heuristically)
        pad_left = int(face_w * 1.0)
        pad_right = int(face_w * 1.0)
        pad_top = int(face_h * 1.0)
        pad_bottom = int(face_h * 1.0)

        crop_x1 = max(0, x1 - pad_left)
        crop_y1 = max(0, y1 - pad_top)
        crop_x2 = min(image.shape[1], x2 + pad_right)
        crop_y2 = min(image.shape[0], y2 + pad_bottom)

        # Ensure crop is at least as big as face box
        if crop_x2 - crop_x1 < face_w:
            crop_x2 = min(image.shape[1], crop_x1 + face_w)
        if crop_y2 - crop_y1 < face_h:
            crop_y2 = min(image.shape[0], crop_y1 + face_h)

        cropped_image = image[crop_y1:crop_y2, crop_x1:crop_x2]
        if cropped_image is None or cropped_image.size == 0:
            raise ValueError("Failed to crop around the detected face.")

        if width is None or height is None or unit is None:
            raise ValueError("Missing required parameters: width, height, unit.")

        unit = str(unit).lower().strip()

        # Convert user dimensions to pixels
        if unit == "px":
            target_w = int(width)
            target_h = int(height)
        elif unit == "inch":
            target_w = int(width * dpi)
            target_h = int(height * dpi)
        elif unit == "mm":
            target_w = int((width / 25.4) * dpi)
            target_h = int((height / 25.4) * dpi)
        else:
            raise ValueError("Invalid unit. Use one of: px, inch, mm.")

        if target_w <= 0 or target_h <= 0:
            raise ValueError("width/height must result in positive pixel dimensions.")

        # Resize and center-crop to target dimensions
        h, w = cropped_image.shape[:2]
        if h == 0 or w == 0:
            raise ValueError("Invalid crop dimensions.")

        aspect_ratio_input = w / h
        aspect_ratio_target = target_w / target_h

        # Scale so smaller side fits, larger side will overflow
        if aspect_ratio_input > aspect_ratio_target:
            # Wider → fit height
            new_h = target_h
            new_w = max(1, int(aspect_ratio_input * new_h))
        else:
            # Taller → fit width
            new_w = target_w
            new_h = max(1, int(new_w / aspect_ratio_input))

        # Guard against rounding leading to (new_w/new_h) slightly smaller than target.
        new_w = max(target_w, new_w)
        new_h = max(target_h, new_h)

        resized = cv2.resize(cropped_image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

        x_start = max(0, (new_w - target_w) // 2)
        y_start = max(0, (new_h - target_h) // 2)
        cropped_image = resized[y_start : y_start + target_h, x_start : x_start + target_w]

        if cropped_image is None or cropped_image.size == 0:
            raise ValueError("Failed during resize/center-crop.")

        # Remove background
        cropped_rgb = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB)
        cropped_pil = Image.fromarray(cropped_rgb)

        buf = BytesIO()
        cropped_pil.save(buf, format="PNG")
        buf.seek(0)

        result_bytes = rembg.remove(buf.getvalue(), session=_rembg_session)
        result_image = Image.open(BytesIO(result_bytes)).convert("RGB")

        os.makedirs(_config.IMAGE_PATH, exist_ok=True)
        output_path = f"{_config.IMAGE_PATH}{filename}"
        result_image.save(output_path, "WEBP")

        image_url = f"{_config.IMAGE_URL_PREFIX}results/{filename}"
        return {
            "message": "Face detected and cropped successfully",
            "image_url": image_url,
            "filename": filename,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))



async def detect_face_and_crop(file: UploadFile, width: float, height: float, unit: str, dpi: int = 96) -> dict:
    """
    Async API-facing wrapper.
    Reads the upload, converts to cv2 image, and runs CPU-heavy logic in thread pool.
    """

    if face_model is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Face detection model is not initialized on the server."
        )

    pil_image = await read_image(file)
    pil_image = pil_image.convert("RGB")
    cv2_image = convert_to_cv2Image(pil_image)

    output_filename = generate_unique_path(file.filename or "image.png")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool,
        detect_face_and_crop_image,
        cv2_image,
        width,
        height,
        unit,
        dpi,
        output_filename,
        face_model,
    )


#===============================================================================================
"""
# This Function swap faces between 2 images (source and target image)
# Source image should have only one face available
# Target image can have 1 or more faces available for swapping
"""
def _detect_faces(image, model):
    faces = model.get(image)
    return faces, len(faces) if faces else 0


def _swap_face_on_target(swapper_model, target_image, target_face, source_face):
    """
    InsightFace in-swapper API: swapper.get(target_img, target_face, source_face, paste_back=True)
    """
    if swapper_model is None:
        raise ValueError("Face swapper model is not loaded on the server.")
    swapped = swapper_model.get(target_image, target_face, source_face, paste_back=True)
    return swapped


def _enhance_image(image, enhancer):
    """
    GFPGANer.enhance(...) returns a tuple; we take the restored image.
    If enhancer isn't available, return image unchanged.
    """
    if enhancer is None:
        return image
    try:
        out = enhancer.enhance(image, has_aligned=False, only_center_face=False, paste_back=True)
        # common shapes: (cropped_faces, restored_faces, restored_img) or (restored_img, ...)
        if isinstance(out, tuple):
            for item in reversed(out):
                if isinstance(item, np.ndarray):
                    return item
            return out[-1]
        return out
    except Exception:
        # Enhancement is optional; don't fail swap if enhancer errors out
        return image


def face_swap_func(source, target, swapper_model, model, enhancer, src_filename, tgt_filename):
    """
    Synchronous worker that performs face swap.
    """
    start_time = time.time()

    if source is None:
        raise ValueError("Source image is missing.")
    if target is None:
        raise ValueError("Target image is missing.")
    if model is None:
        raise ValueError("Face detection model is not loaded on the server.")

    # Detect faces in source
    source_faces, num_src_faces = _detect_faces(source, model)
    if num_src_faces < 1:
        raise ValueError("No face detected in source image.")
    if num_src_faces > 1:
        raise ValueError("Source image must contain exactly one face.")
    detected_src_face = source_faces[0]

    # Detect faces in target
    target_faces, num_tgt_faces = _detect_faces(target, model)
    if num_tgt_faces < 1:
        raise ValueError("No face detected in target image.")

    # Swap faces on target image
    swapped_target = target
    for tgt_face in target_faces:
        swapped_target = _swap_face_on_target(swapper_model, swapped_target, tgt_face, detected_src_face)

    if swapped_target is None or getattr(swapped_target, "size", 0) == 0:
        raise ValueError("Failed to swap faces.")

    enhanced_output_image = _enhance_image(swapped_target, enhancer)
    if enhanced_output_image is None or getattr(enhanced_output_image, "size", 0) == 0:
        raise ValueError("Failed to produce output image.")

    output_filename = generate_unique_path(tgt_filename or "target.png")
    image_url = save_img_with_url(enhanced_output_image, output_filename)
    end_time = time.time()

    return {
        "message": "Faces swapped successfully",
        "image_url": image_url,
        "filename": output_filename,
        "time_taken": f"{end_time - start_time:.2f}",
    }


async def face_swap(source_file: UploadFile, target_file: UploadFile) -> dict:
    """
    Async API wrapper. Reads uploads, converts to cv2, runs face swap in thread pool.
    """
    if face_model is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Face detection model is not initialized on the server.",
        )
    if swapper is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Face swapper model is not initialized on the server.",
        )

    src_pil = await read_image(source_file)
    tgt_pil = await read_image(target_file)
    src_cv2 = convert_to_cv2Image(src_pil.convert("RGB"))
    tgt_cv2 = convert_to_cv2Image(tgt_pil.convert("RGB"))

    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(
            thread_pool,
            face_swap_func,
            src_cv2,
            tgt_cv2,
            swapper,
            face_model,
            gfpgan_model,
            source_file.filename or "source.png",
            target_file.filename or "target.png",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))