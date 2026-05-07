import os
from config.index import GFPGAN1_3_ENABLE, GFPGAN1_4_ENABLE
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