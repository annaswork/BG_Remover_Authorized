from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from controller.auth_controller import require_api_key
from controller.face_app_controller import detect_face_and_crop


router = APIRouter(prefix="/api/face_detect", tags=["face"])


@router.post("/", response_model=dict)
@router.post("/face-crop", response_model=dict)
async def face_crop(
    file: UploadFile = File(..., description="Image file to process"),
    width: float = Form(..., gt=0, description="Target width"),
    height: float = Form(..., gt=0, description="Target height"),
    unit: str = Form(..., description="Unit for width/height: px, inch, mm"),
    dpi: int = Form(96, ge=1, description="DPI used when unit is inch/mm"),
    _auth: dict = Depends(require_api_key),
):
    """
    Detect exactly one face, crop around it, resize/center-crop to target dimensions,
    remove background, and return the cropped face image URL.
    Requires a valid API key in the X-API-Key header.
    """
    try:
        return await detect_face_and_crop(file=file, width=width, height=height, unit=unit, dpi=dpi)
    except HTTPException:
        raise
    except Exception as e:
        # Safety net: controller should already normalize most errors.
        raise HTTPException(status_code=400, detail=str(e))

