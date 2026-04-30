import insightface
from insightface.app import FaceAnalysis
import os
from gfpgan import GFPGANer
import traceback

from config.index import (
    DETECTION_MODEL_NAME,
    DETECTION_MODEL_ROOT,
    DETECTION_MODEL_CTX_ID,
    GFPGAN_V1_3_PATH,
    GFPGAN_V1_4_PATH,
    GFPGAN1_3_ENABLE,
    GFPGAN1_4_ENABLE,
    INSWAPPER_ENABLE,
    MODEL_PATH,
)

def _load_face_model() -> FaceAnalysis:
    os.makedirs(DETECTION_MODEL_ROOT, exist_ok=True)

    face_analysis = FaceAnalysis(
        name=DETECTION_MODEL_NAME,
        root=DETECTION_MODEL_ROOT,
    )

    try:
        face_analysis.prepare(ctx_id=DETECTION_MODEL_CTX_ID)
        return face_analysis
    except Exception:
        if DETECTION_MODEL_CTX_ID == -1:
            raise

        # GPU (or selected ctx) failed; fallback to CPU.
        try:
            face_analysis.prepare(ctx_id=-1)
            return face_analysis
        except Exception:
            raise

try:
    FACE_MODEL: FaceAnalysis = _load_face_model()
except Exception as e:
    print(f"[ERROR] Failed to load face detection model: {e}")
    print(traceback.format_exc())
    raise RuntimeError("Failed to load face detection model.") from e

#===========================================================================================================================

#Load Swapper Model
if INSWAPPER_ENABLE:
    try:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at: {MODEL_PATH}")
        
        FACE_SWAPPER_MODEL = insightface.model_zoo.get_model(
            MODEL_PATH,
            download=False,
            download_zip=False
        )
    except Exception as e:
        print(f"[ERROR] Failed to load face swapper model: {e}")
        FACE_SWAPPER_MODEL = None
else:
    FACE_SWAPPER_MODEL = None

#===========================================================================================================================

#Load GFPGANv1.3
if GFPGAN1_3_ENABLE:
    try:
        GFPGAN_V1_3_MODEL = GFPGANer(
            model_path=GFPGAN_V1_3_PATH,
            upscale=1,
            arch="clean",
            channel_multiplier=2,
            bg_upsampler=None,
            device="cpu",
        )
    except Exception as e:
        print(f"[ERROR] Failed to load GFPGAN 1.3 model: {e}")
        GFPGAN_V1_3_MODEL = None
else:
    GFPGAN_V1_3_MODEL = None

#===========================================================================================================================

#Load GFPGANv1.4
if GFPGAN1_4_ENABLE:
    try:
        GFPGAN_V1_4_MODEL = GFPGANer(
            model_path=GFPGAN_V1_4_PATH,
            upscale=1,
            arch="clean",
            channel_multiplier=2,
            bg_upsampler=None,
            device="cpu",
        )
    except Exception as e:
        print(f"[ERROR] Failed to load GFPGAN 1.4 model: {e}")
        GFPGAN_V1_4_MODEL = None
else:
    GFPGAN_V1_4_MODEL = None
