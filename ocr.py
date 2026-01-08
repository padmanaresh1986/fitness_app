# app/ocr.py
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image, ImageOps

from config import settings


# Configure Tesseract binary path
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


def _preprocess_image(image: Image.Image) -> Image.Image:
    """
    Basic preprocessing to improve OCR:
    - Convert to grayscale
    - Increase contrast / apply threshold if needed
    """
    gray = ImageOps.grayscale(image)
    # You can add more preprocessing here if required (binarization, resizing, etc.)
    return gray


def ocr_image(image_path: Path) -> str:
    """
    Run OCR on a single image and return plain text.
    """
    img = Image.open(image_path)
    img = _preprocess_image(img)

    config = f"--psm {settings.TESSERACT_PSM} --oem {settings.TESSERACT_OEM}"
    text = pytesseract.image_to_string(
        img,
        lang=settings.TESSERACT_LANG,
        config=config,
    )
    return text.strip()
