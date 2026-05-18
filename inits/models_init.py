import os
from config.index import (
    GFPGAN1_3_ENABLE,
    GFPGAN1_4_ENABLE,
    LAMA_ENABLE,
    SAM_ENABLE,
    LAMA_MODEL_TYPE,
    SAM_MODEL_TYPE,
    OBJECT_REMOVER_DEVICE,
)
from models import load_models

face_model = load_models.FACE_MODEL
swapper = load_models.FACE_SWAPPER_MODEL

gfpgan_model = None
if GFPGAN1_3_ENABLE:
    gfpgan_model = load_models.GFPGAN_V1_3_MODEL
elif GFPGAN1_4_ENABLE:
    gfpgan_model = load_models.GFPGAN_V1_4_MODEL

# Plant identification models/resources
bioclip_model = load_models.BIOCLIP_MODEL
bioclip_preprocess = load_models.BIOCLIP_PREPROCESS
faiss_index = load_models.FAISS_INDEX
plant_metadata = load_models.PLANT_METADATA

# ── PlantProfiler (optional - only if OpenAI API key is set) ──────────────────
plant_profiler = None
if os.getenv("OPENAI_API_KEY"):
    try:
        from utils.slm_plant_profile import PlantProfiler
        plant_profiler = PlantProfiler()
        print("[Models Init] PlantProfiler initialized successfully")
    except Exception as e:
        print(f"[Models Init] Warning: Could not initialize PlantProfiler: {e}")
        print("[Models Init] Plant profile generation will not be available")
else:
    print("[Models Init] Warning: OPENAI_API_KEY not set in .env file")
    print("[Models Init] Plant profile generation will not be available")

# ── Object Remover Models (LaMa + SAM) ────────────────────────────────────────
lama_model = None
sam_processor = None

if LAMA_ENABLE:
    try:
        from iopaint.model_manager import ModelManager
        from iopaint.schema import HDStrategy, SDSampler
        
        print(f"[Models Init] Loading LaMa model ({LAMA_MODEL_TYPE}) on {OBJECT_REMOVER_DEVICE}...")
        lama_model = ModelManager(
            name=LAMA_MODEL_TYPE,
            device=OBJECT_REMOVER_DEVICE,
            hf_access_token=None,
            disable_nsfw=False,
            sd_cpu_textencoder=False,
            local_files_only=False,
            cpu_offload=False,
        )
        print("[Models Init] LaMa model loaded successfully")
    except Exception as e:
        print(f"[Models Init] Warning: Could not load LaMa model: {e}")
        print("[Models Init] Object removal inpainting will not be available")
else:
    print("[Models Init] LaMa model disabled (LAMA_ENABLE=false)")

if SAM_ENABLE:
    try:
        from utils.sam_process import SAMProcessor
        
        print(f"[Models Init] Loading SAM model ({SAM_MODEL_TYPE}) on {OBJECT_REMOVER_DEVICE}...")
        sam_processor = SAMProcessor(
            model_type=SAM_MODEL_TYPE,
            device=OBJECT_REMOVER_DEVICE,
        )
        print("[Models Init] SAM model loaded successfully")
    except Exception as e:
        print(f"[Models Init] Warning: Could not load SAM model: {e}")
        print("[Models Init] SAM segmentation will not be available")
else:
    print("[Models Init] SAM model disabled (SAM_ENABLE=false)")