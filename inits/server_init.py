import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

#Thread pool for creating threads
from concurrent.futures import ThreadPoolExecutor

#importing python dependencies
import pillow_heif

#import Environment variables
import config.index as config_

#============================================================================

#INITIALIZE THE FASTAPI APP
app = FastAPI(
    title=config_.TITLE,
    description=config_.DESCRIPTION,
    version=config_.VERSION,
    author=config_.AUTHOR
)

#Create and mount templates folder
os.makedirs(config_.TEMPLATES_DIR, exist_ok=True)
app.mount(
    f"/{config_.TEMPLATES_DIR}",
    Jinja2Templates(directory=config_.TEMPLATES_DIR),
    name=config_.TEMPLATES_DIR
)

#Create and mount static folder
os.makedirs(config_.STATIC_DIR, exist_ok=True)
app.mount(
    f"/{config_.STATIC_DIR}",
    StaticFiles(directory=config_.STATIC_DIR),
    name=config_.STATIC_DIR
)

#============================================================================
#configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#============================================================================
#configure Thread Pool Executor
thread_pool = ThreadPoolExecutor(max_workers=10)

#============================================================================
#configure Pillow-HEIF plugin
pillow_heif.register_heif_opener()

#============================================================================