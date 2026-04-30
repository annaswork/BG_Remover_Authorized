def _detect_faces(image, model):
    faces = model.get(image)
    return faces, len(faces) if faces else 0


def _swap_face_on_target(swapper_model, target_image, target_face, source_face):
    """
    InsightFace in-swapper API: swapper.get(target_img, target_face, source_face, paste_back=True)
    """
    if swapper_model is None:
        raise ValueError("Face swapper model is not loaded on the server.")
    swapped = swapper_model.get(target_image, target_face, source_face, paste_back=True)
    return swapped
