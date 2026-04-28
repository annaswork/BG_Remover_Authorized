import cv2
from config.index import IMAGE_URL_PREFIX, IMAGE_PATH

def save_img_with_url(
    output_file,
    output_filename
):

    save_success = cv2.imwrite(
        f"{IMAGE_PATH}/{output_filename}",
        output_file
    )

    if not save_success:
        raise ValueError(f"Failed to save image on {IMAGE_PATH}")

    print(f"File saved at path: {IMAGE_PATH}")

    image_url = f"{IMAGE_URL_PREFIX}/results/{output_filename}"

    return image_url