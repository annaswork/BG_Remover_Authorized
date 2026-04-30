import os
import requests
import gdown

#URLS
from models.url_paths import INSWAPPER_128, GFPGAN_V1_4

#Importing models enabling flag
from config.index import INSWAPPER_ENABLE, GFPGAN1_4_ENABLE, GFPGAN1_3_ENABLE

def download_http(url: str, filename: str):
    print(f"Downloading {filename}........")
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(filename, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Saved to {filename}")


#1: Inswapper
if INSWAPPER_ENABLE:
    inswapper_out = os.path.join("models", "inswapper_128.onnx")
    if os.path.exists(inswapper_out):
        print(f"Skipping {inswapper_out}, file already exists.")
    else:
        print("Downloading INSWAPPER via gdown...")
        gdown.download(INSWAPPER_128, inswapper_out, quiet=False, fuzzy=True)

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


print("All downloads completed")