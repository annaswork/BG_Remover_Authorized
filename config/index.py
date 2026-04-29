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