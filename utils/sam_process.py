"""
SAM segmentation for the object-remover API.

Wraps IOPaint's InteractiveSeg (Segment Anything / SAM2) so weights are
resolved via IOPaint's downloader and architecture matches LaMa/IOPaint.
"""

from __future__ import annotations

import hashlib
from typing import List, Sequence, Union

import numpy as np

from iopaint.plugins.interactive_seg import InteractiveSeg


class SAMProcessor:
    """Load SAM / SAM2 once and produce uint8 masks (255 = foreground)."""

    def __init__(self, model_type: str, device: str):
        self._seg = InteractiveSeg(model_name=model_type, device=device)

    def generate_mask(
        self,
        image_rgb: np.ndarray,
        points: Sequence[Sequence[int]],
        labels: Sequence[int],
    ) -> np.ndarray:
        """
        Args:
            image_rgb: HxWx3 RGB, uint8.
            points: [[x, y], ...] in pixel coordinates (same space as image_rgb).
            labels: 1 = foreground click, 0 = background (SAM convention).

        Returns:
            HxW uint8 mask, 255 on the selected region.
        """
        if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
            raise ValueError("image_rgb must be HxWx3 RGB")
        if len(points) != len(labels):
            raise ValueError("points and labels must have the same length")

        clicks: List[List[Union[int, float]]] = [
            [int(p[0]), int(p[1]), int(labels[i])] for i, p in enumerate(points)
        ]
        img_md5 = hashlib.md5(np.ascontiguousarray(image_rgb).tobytes()).hexdigest()
        return self._seg.forward(image_rgb, clicks, img_md5)