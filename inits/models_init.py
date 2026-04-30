from config.index import GFPGAN1_3_ENABLE, GFPGAN1_4_ENABLE
from models import load_models

face_model = load_models.FACE_MODEL
swapper = load_models.FACE_SWAPPER_MODEL

gfpgan_model = None
if GFPGAN1_3_ENABLE:
    gfpgan_model = load_models.GFPGAN_V1_3_MODEL
elif GFPGAN1_4_ENABLE:
    gfpgan_model = load_models.GFPGAN_V1_4_MODEL