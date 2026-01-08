# app/local_images.py
from __future__ import annotations

from pathlib import Path
from typing import List

from config import settings


def get_local_folder_path(folder_name: str) -> Path:
    """
    Build absolute path for a given date folder under Google Drive Desktop.

    Example:
      folder_name = "06-01-2026"
      => G:\My Drive\06-01-2026
    """
    base = Path(settings.LOCAL_DRIVE_BASE)
    return base / folder_name


def list_folder_images(folder_name: str) -> List[Path]:
    """
    Return all image files (jpg, jpeg, png, webp, heic, etc.) in the given local folder.
    """
    folder_path = get_local_folder_path(folder_name)

    if not folder_path.exists() or not folder_path.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic"}

    image_paths: List[Path] = []
    for p in folder_path.iterdir():
        if p.is_file() and p.suffix.lower() in exts:
            image_paths.append(p)

    return image_paths
