import os
from dotenv import load_dotenv

load_dotenv()

IP = "172.16.0.94"
PORT = 8000

#App Information
TITLE = "Background Remover"
DESCRIPTION = "Remove background from images using AI"
VERSION = "1.0.0"
AUTHOR = "Annas Asif"


#Templates Path
TEMPLATES_DIR = "templates"

#Static Path
STATIC_DIR = "static"

#Database Information
MONGODB_URL = "mongodb://localhost:27017"
ANALYTICS_DATABASE = "analytics"
AUTHORIZATION_DATABASE = "authorization"

SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
ANALYTICS_COLLECTION_NAME = "api_logs"
AUTHORIZATION_COLLECTION_NAME = "api_keys"

#Image Path and URL Prefix
IMAGE_PATH = "static/results/"
IMAGE_URL_PREFIX = f"http://{IP}:{PORT}/static/"

#InsightFace variables
INSIGHTFACE_MODEL = "buffalo_l"
INSIGHTFACE_MODEL_ROOT = f"C:/Users/muhammadannasasif/.insightface"

# --------------------------------------------------------------------------------------
# Models / paths
# --------------------------------------------------------------------------------------

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Face detection (InsightFace FaceAnalysis)
DETECTION_MODEL_NAME = os.getenv("DETECTION_MODEL_NAME", INSIGHTFACE_MODEL)
DETECTION_MODEL_ROOT = os.getenv("DETECTION_MODEL_ROOT", INSIGHTFACE_MODEL_ROOT)

try:
    DETECTION_MODEL_CTX_ID = int(os.getenv("DETECTION_MODEL_CTX_ID", "-1"))
except ValueError:
    DETECTION_MODEL_CTX_ID = -1

# Face swapper (inswapper_128.onnx)
MODEL_PATH = os.getenv(
    "INSWAPPER_MODEL_PATH",
    os.path.join(ROOT_DIR, "models", "inswapper_128.onnx"),
)

# GFPGAN weights
# GFPGAN_V1_3_PATH is kept for compatibility, but v1.3 is currently not used.
GFPGAN_V1_3_PATH = os.getenv(
    "GFPGAN_V1_3_PATH",
    os.path.join(ROOT_DIR, "models", "GFPGANv1.3.pth"),
)
GFPGAN_V1_4_PATH = os.getenv(
    "GFPGAN_V1_4_PATH",
    os.path.join(ROOT_DIR, "models", "GFPGANv1.4.pth"),
)

# Models to use (Face Swap)
INSWAPPER_ENABLE = True
# GFPGAN1_3_ENABLE = True  # optional
GFPGAN1_3_ENABLE = False
GFPGAN1_4_ENABLE = True