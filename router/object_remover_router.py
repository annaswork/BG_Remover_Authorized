from fastapi import APIRouter, UploadFile, File, Form, Depends, Request
from controller.auth_controller import require_api_key
from controller.object_remover_controller import (
    health,
    inpaint_base64,
    inpaint_file,
    sam_segment,
    clear_results,
)

router = APIRouter(prefix="/api/object-remover", tags=["object-remover"])


@router.get("/health", response_model=dict)
async def health_check():
    """
    Returns load status of LaMa and SAM models.
    No auth required — safe to call from admin panel dashboards.
    """
    return await health()


@router.post("/inpaint", response_model=dict)
async def inpaint_json(
    request: Request,
    _auth: dict = Depends(require_api_key),
):
    """
    Erase an object using base64-encoded image + mask.

    Body (JSON):
      image                    : base64 string — source image
      mask                     : base64 string — B&W PNG (white = erase)
      ldmSteps                 : int  (default 25)
      hdStrategy               : str  "Original" | "Crop" | "Resize"  (default "Original")
      hdStrategyCropMargin     : int  (default 128)
      hdStrategyCropTrigerSize : int  (default 800)
      hdStrategyResizeLimit    : int  (default 2048)
      maskExpand               : int  (default 10)

    Requires X-API-Key header.
    """
    body = await request.json()
    return await inpaint_base64(body, request)


@router.post("/inpaint-file", response_model=dict)
async def inpaint_multipart(
    request: Request,
    image: UploadFile = File(..., description="Source image file (JPEG / PNG)"),
    mask: UploadFile  = File(..., description="B&W mask file — white areas will be erased"),
    ldmSteps: int                 = Form(25),
    hdStrategy: str               = Form("Original"),
    hdStrategyCropMargin: int     = Form(128),
    hdStrategyCropTrigerSize: int = Form(800),
    hdStrategyResizeLimit: int    = Form(2048),
    maskExpand: int               = Form(10),
    _auth: dict = Depends(require_api_key),
):
    """
    Erase an object using multipart file uploads.
    Requires X-API-Key header.
    """
    return await inpaint_file(
        image=image,
        mask=mask,
        request=request,
        ldmSteps=ldmSteps,
        hdStrategy=hdStrategy,
        hdStrategyCropMargin=hdStrategyCropMargin,
        hdStrategyCropTrigerSize=hdStrategyCropTrigerSize,
        hdStrategyResizeLimit=hdStrategyResizeLimit,
        maskExpand=maskExpand,
    )


@router.post("/sam", response_model=dict)
async def sam_segmentation(
    image: UploadFile = File(..., description="Source image file (JPEG / PNG)"),
    points: str       = Form(..., description='JSON array e.g. [{"x":100,"y":200}]'),
    _auth: dict = Depends(require_api_key),
):
    """
    Generate a segmentation mask from user click points using SAM.
    Returns {"mask": "<base64-encoded PNG>"}.
    Requires X-API-Key header.
    """
    return await sam_segment(image=image, points=points)


@router.delete("/clear-results", response_model=dict)
async def clear_result_files(_auth: dict = Depends(require_api_key)):
    """
    Delete all saved inpainted result images.
    Requires X-API-Key header.
    """
    return await clear_results()