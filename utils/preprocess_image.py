import uuid
import cv2
import numpy as np
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageOps

async def read_image(file):
    content = await file.read()

    image = Image.open(BytesIO(content))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    return image

def convert_to_cv2Image(image):
    image_array = np.array(image)
    new_image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)

    return new_image

def generate_unique_path(filename):
    unique_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    output_file_path = f"{filename.split('.')[0]}_{unique_id}_{timestamp}.webp".replace(" ","_")

    return output_file_path

async def create_thumbnail(image_path, output_path):
    with Image.open(image_path) as img:
        #1. Calculate new dimensions
        original_width, original_height = img.size
        new_size = (original_width // 3, original_height // 3)

        #2. Resizing using Lanczos resampling for high quality
        img.thumbnail(new_size, Image.Resampling.LANCZOS)

        #3. Convert to numpy and save with OpenCV (avoids Pillow libwebp dependency)
        import numpy as np
        import cv2
        if img.mode == "RGBA":
            img_array = np.array(img)
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGRA)
        else:
            img_array = np.array(img.convert("RGB"))
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, img_cv, [cv2.IMWRITE_WEBP_QUALITY, 70])
