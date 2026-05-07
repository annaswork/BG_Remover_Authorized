import insightface
from insightface.app import FaceAnalysis
import os
from gfpgan import GFPGANer
import traceback
import torch
import open_clip
import faiss
import numpy as np
import requests
import time

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
    BIOCLIP_PATH,
    BIOCLIP_ENABLE,
    FAISS_ENABLE,
    FAISS_INDEX_PATH,
    PLANT_METADATA_PATH,
)

def _download_with_resume(url: str, output_path: str, max_retries: int = 10, chunk_size: int = 1024 * 1024):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    part_path = f"{output_path}.part"

    for attempt in range(1, max_retries + 1):
        existing_size = os.path.getsize(part_path) if os.path.exists(part_path) else 0
        headers = {"Range": f"bytes={existing_size}-"} if existing_size > 0 else {}
        mode = "ab" if existing_size > 0 else "wb"

        try:
            with requests.get(url, stream=True, timeout=60, headers=headers) as resp:
                if existing_size > 0 and resp.status_code == 200:
                    # Server ignored Range; restart from scratch to avoid corrupt output.
                    existing_size = 0
                    headers = {}
                    mode = "wb"
                    resp.close()
                    with requests.get(url, stream=True, timeout=60) as retry_resp:
                        retry_resp.raise_for_status()
                        with open(part_path, mode) as f:
                            for chunk in retry_resp.iter_content(chunk_size=chunk_size):
                                if chunk:
                                    f.write(chunk)
                else:
                    resp.raise_for_status()
                    with open(part_path, mode) as f:
                        for chunk in resp.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)

            os.replace(part_path, output_path)
            return
        except Exception as e:
            if attempt == max_retries:
                raise RuntimeError(
                    f"Failed downloading {output_path} after {max_retries} attempts: {e}"
                ) from e

            print(f"[WARN] Download interrupted (attempt {attempt}/{max_retries}): {e}")
            print("Retrying with resume...")
            time.sleep(min(2 * attempt, 15))

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

#===========================================================================================================================

#Load BioCLIP Model
if BIOCLIP_ENABLE:
    try:
        if not os.path.exists(BIOCLIP_PATH):
            print(f"BioCLIP model not found at {BIOCLIP_PATH}")
            print("Downloading BioCLIP model from Hugging Face...")
            
            from models.url_paths import BIOCLIP
            bioclip = BIOCLIP
            
            # Download with retry + resume support for unstable connections.
            _download_with_resume(url=bioclip, output_path=BIOCLIP_PATH)
            print(f"Successfully downloaded BioCLIP model to {BIOCLIP_PATH}")
        
        print(f"Loading BioCLIP model from {BIOCLIP_PATH}...")
        BIOCLIP_MODEL, _, BIOCLIP_PREPROCESS = open_clip.create_model_and_transforms(
            'ViT-H-14',
            pretrained=BIOCLIP_PATH,
            weights_only=False,
        )
        BIOCLIP_MODEL.eval()
        print("BioCLIP model loaded successfully")
    except Exception as e:
        print(f"[ERROR] Failed to load BioCLIP model: {e}")
        print(traceback.format_exc())
        BIOCLIP_MODEL = None
        BIOCLIP_PREPROCESS = None
else:
    BIOCLIP_MODEL = None
    BIOCLIP_PREPROCESS = None
#===========================================================================================================================

#Load FAISS Index
if FAISS_ENABLE:
    try:
        if not os.path.exists(FAISS_INDEX_PATH):
            print(f"FAISS index not found at {FAISS_INDEX_PATH}")
            print("Downloading FAISS index from Google Drive...")
            
            # Import gdown for downloading
            import gdown
            from models.url_paths import PLANT_FAISS_INDEX
            
            # Create models directory if it doesn't exist
            os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)
            
            # Download the FAISS index
            gdown.download(url=PLANT_FAISS_INDEX, output=FAISS_INDEX_PATH, quiet=False)
            print(f"Successfully downloaded FAISS index to {FAISS_INDEX_PATH}")
        
        print(f"Loading FAISS index from {FAISS_INDEX_PATH}...")
        FAISS_INDEX = faiss.read_index(FAISS_INDEX_PATH)
        print(f"FAISS index loaded successfully with {FAISS_INDEX.ntotal} vectors")
    except Exception as e:
        print(f"[ERROR] Failed to load FAISS index: {e}")
        print(traceback.format_exc())
        FAISS_INDEX = None
else:
    FAISS_INDEX = None

#===========================================================================================================================

# Load Plant Metadata
if FAISS_ENABLE:
    try:
        if not os.path.exists(PLANT_METADATA_PATH):
            print(f"Plant metadata not found at {PLANT_METADATA_PATH}")
            print("Downloading plant metadata from Google Drive...")
            
            # Import gdown for downloading
            import gdown
            from models.url_paths import EMBEDDINGS_FOLDER_ID
            
            # Create embeddings directory if it doesn't exist
            embeddings_dir = os.path.dirname(PLANT_METADATA_PATH)
            os.makedirs(embeddings_dir, exist_ok=True)
            
            # Download the entire folder using folder ID
            try:
                gdown.download_folder(id=EMBEDDINGS_FOLDER_ID, output=embeddings_dir, quiet=False, use_cookies=False)
                print(f"Successfully downloaded plant metadata to {embeddings_dir}")
            except Exception as download_error:
                print(f"Failed to download embeddings folder: {download_error}")
                print("Please manually download the folder from Google Drive and place it in models/embeddings_h14/")
                raise
        
        print(f"Loading plant metadata from {PLANT_METADATA_PATH}...")
        import json
        with open(PLANT_METADATA_PATH, 'r', encoding='utf-8') as f:
            PLANT_METADATA = json.load(f)
        print(f"Plant metadata loaded successfully with {len(PLANT_METADATA)} entries")
    except Exception as e:
        print(f"[ERROR] Failed to load plant metadata: {e}")
        print(traceback.format_exc())
        PLANT_METADATA = None
else:
    PLANT_METADATA = None

# Plant embeddings vectors - set to None (not using embeddings file)
PLANT_EMBEDDINGS_VECTORS = None