import numpy as np


def _enhance_image(image, enhancer):
    """
    GFPGANer.enhance(...) returns a tuple; we take the restored image.
    If enhancer isn't available, return image unchanged.
    """
    if enhancer is None:
        return image
    try:
        out = enhancer.enhance(image, has_aligned=False, only_center_face=False, paste_back=True)
        # common shapes: (cropped_faces, restored_faces, restored_img) or (restored_img, ...)
        if isinstance(out, tuple):
            for item in reversed(out):
                if isinstance(item, np.ndarray):
                    return item
            return out[-1]
        return out
    except Exception:
        # Enhancement is optional; don't fail swap if enhancer errors out
        return image
