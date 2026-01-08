# config.py
import os
from pathlib import Path


class Settings:
    # Tesseract config
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    TESSERACT_LANG: str = os.getenv("TESSERACT_LANG", "eng")

    # Local Google Drive base (Desktop client)
    # Example: G:\My Drive
    LOCAL_DRIVE_BASE: str = os.getenv("LOCAL_DRIVE_BASE", r"C:\Data\fitin50\Fitness_Challenge_Attachments")

    # Optional cache dir
    DOWNLOAD_ROOT_DIR: str = os.getenv("DOWNLOAD_ROOT_DIR", "data/downloads")

    # Ollama config
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")

    # OCR tuning
    TESSERACT_PSM: int = int(os.getenv("TESSERACT_PSM", "6"))
    TESSERACT_OEM: int = int(os.getenv("TESSERACT_OEM", "3"))


settings = Settings()
