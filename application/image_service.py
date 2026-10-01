"""Validate an uploaded image before the data-layer Vision index searches it."""
from pathlib import Path

from PIL import Image


class ImageService:
    WHITE_THRESHOLD = 242

    @staticmethod
    def validate(image_path):
        path = Path(image_path).resolve()
        with Image.open(path) as source:
            extrema = source.convert("RGB").resize((64, 64)).getextrema()
        if all(low > ImageService.WHITE_THRESHOLD for low, _ in extrema):
            raise ValueError("Image has no foreground object")
        return path
