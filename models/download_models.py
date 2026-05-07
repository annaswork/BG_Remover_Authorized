import os
import requests
import gdown
import sys
import time

# Ensure we can import from the project root even if run from inside 'models/'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# URLS
try:
    from models.url_paths import INSWAPPER_128, GFPGAN_V1_4, BIOCLIP, PLANT_FAISS_INDEX, EMBEDDINGS_FOLDER_ID
except ImportError:
    from url_paths import INSWAPPER_128, GFPGAN_V1_4, BIOCLIP, PLANT_FAISS_INDEX, EMBEDDINGS_FOLDER_ID

# Importing models enabling flag
try:
    from config.index import INSWAPPER_ENABLE, GFPGAN1_4_ENABLE, GFPGAN1_3_ENABLE, FAISS_ENABLE, FAISS_INDEX_PATH, PLANT_METADATA_PATH
except ImportError:
    from config import INSWAPPER_ENABLE, GFPGAN1_4_ENABLE, GFPGAN1_3_ENABLE, FAISS_ENABLE, FAISS_INDEX_PATH, PLANT_METADATA_PATH

#Importing models enabling flag
from config.index import INSWAPPER_ENABLE, GFPGAN1_4_ENABLE, GFPGAN1_3_ENABLE

def download_http(url: str, filename: str, max_retries: int = 10, chunk_size: int = 1024 * 1024):
    print(f"Downloading {filename}........")
    part_file = f"{filename}.part"
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    for attempt in range(1, max_retries + 1):
        existing_size = os.path.getsize(part_file) if os.path.exists(part_file) else 0
        headers = {"Range": f"bytes={existing_size}-"} if existing_size > 0 else {}
        mode = "ab" if existing_size > 0 else "wb"
        try:
            with requests.get(url, stream=True, timeout=60, headers=headers) as r:
                if existing_size > 0 and r.status_code == 200:
                    # Range not honored, restart safely.
                    mode = "wb"
                r.raise_for_status()
                with open(part_file, mode) as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
            os.replace(part_file, filename)
            print(f"Saved to {filename}")
            return
        except Exception as e:
            if attempt == max_retries:
                raise RuntimeError(f"Download failed for {filename}: {e}") from e
            print(f"[WARN] Download interrupted (attempt {attempt}/{max_retries}): {e}")
            print("Retrying with resume...")
            time.sleep(min(2 * attempt, 15))


#1: Inswapper
if INSWAPPER_ENABLE:
    inswapper_out = os.path.join("models", "inswapper_128.onnx")
    if os.path.exists(inswapper_out):
        print(f"Skipping {inswapper_out}, file already exists.")
    else:
        print("Downloading INSWAPPER via gdown...")
        gdown.download(INSWAPPER_128, inswapper_out, quiet=False)

# # 2: GFPGAN v1.3
# if GFPGAN1_3_ENABLE:
#     gfp13_out = os.path.join("models", "GFPGANv1.3.pth")
#     if os.path.exists(gfp13_out):
#         print(f"Skipping {gfp13_out}, file already exists.")
#     else:
#         download_http(GFPGAN_V1_3, gfp13_out)

# 3: GFPGAN v1.4
if GFPGAN1_4_ENABLE:
    gfp14_out = os.path.join("models", "GFPGANv1.4.pth")
    if os.path.exists(gfp14_out):
        print(f"Skipping {gfp14_out}, file already exists.")
    else:
        download_http(GFPGAN_V1_4, gfp14_out)


# 4: BioCLIP
bioclip_out = os.path.join("models", "bioclip_vith14")
if os.path.exists(bioclip_out):
    print(f"Skipping {bioclip_out}, file already exists.")
else:
    print(f"Downloading BioCLIP from {BIOCLIP}...")
    download_http(BIOCLIP, bioclip_out)


# 5: FAISS Index
if FAISS_ENABLE:
    if os.path.exists(FAISS_INDEX_PATH):
        print(f"Skipping {FAISS_INDEX_PATH}, file already exists.")
    else:
        print(f"Downloading FAISS Index from {PLANT_FAISS_INDEX}...")
        gdown.download(url=PLANT_FAISS_INDEX, output=FAISS_INDEX_PATH, quiet=False)

# 6: Plant Metadata (embeddings folder)
if FAISS_ENABLE:
    embeddings_dir = os.path.dirname(PLANT_METADATA_PATH)
    if os.path.exists(PLANT_METADATA_PATH):
        print(f"Skipping {PLANT_METADATA_PATH}, file already exists.")
    else:
        print(f"Downloading Plant Metadata folder from Google Drive...")
        os.makedirs(embeddings_dir, exist_ok=True)
        # Download the entire folder from Google Drive using folder ID
        try:
            gdown.download_folder(id=EMBEDDINGS_FOLDER_ID, output=embeddings_dir, quiet=False, use_cookies=False)
            print(f"Successfully downloaded embeddings folder to {embeddings_dir}")
        except Exception as e:
            print(f"Error downloading embeddings folder: {e}")
            print("Please manually download the folder and place it in models/embeddings_h14/")

print("All downloads completed")