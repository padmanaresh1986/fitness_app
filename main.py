# main.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import pandas as pd

from config import settings
from local_images import list_folder_images
from ocr import ocr_image
from llm_client import extract_health_data_from_text, LLMExtractionError
from models import (
    ProcessFolderRequest,
    ProcessFolderResponse,
    ImageResult,
)
from db import (
    create_tables,
    save_results_to_db,
    FitIn50Workout,
    get_db,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("fitin50")

app = FastAPI(
    title="FitIn50 OCR API",
    description="Process local Google Drive Desktop folder images, extract health stats, store in Postgres, export to Excel",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#@app.on_event("startup")
# def on_startup():
#     # Ensure tables exist (optional if you run SQL manually)
#     create_tables()
#     logger.info("Database tables ensured.")


@app.post("/process-folder", response_model=ProcessFolderResponse)
def process_folder(req: ProcessFolderRequest):
    """
    1. Read all image files from local Google Drive Desktop folder:
         <LOCAL_DRIVE_BASE>/<folder_name>
       Example: G:\\My Drive\\06-01-2026
    2. Run OCR on each image.
    3. Use local Ollama (llama3.1) to parse health stats into JSON.
    4. Store each image result as a row in Postgres.
    5. Return structured response.
    """
    folder_name = req.folder_name

    try:
        logger.info("Listing images for local folder_name=%s", folder_name)
        image_paths: List[Path] = list_folder_images(folder_name)
    except FileNotFoundError as e:
        logger.warning("Folder not found: %s", e)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to list images from local folder")
        raise HTTPException(
            status_code=500,
            detail=f"Error reading local folder: {e}",
        )

    if not image_paths:
        logger.warning("No images found for folder_name=%s", folder_name)
        return ProcessFolderResponse(
            folder_name=folder_name,
            images_processed=0,
            results=[],
        )

    results: List[ImageResult] = []

    for img_path in image_paths:
        logger.info("Processing image: %s", img_path)
        try:
            text = ocr_image(img_path)
        except Exception:
            logger.exception("OCR failed for image %s", img_path)
            # Skip this image; continue with others
            continue

        try:
            health_data = extract_health_data_from_text(text)
        except LLMExtractionError as e:
            logger.warning("LLM extraction failed for image %s: %s", img_path, e)
            raise HTTPException(
                status_code=500,
                detail=f"LLM JSON extraction failed for image {img_path.name}: {e}",
            )
        except Exception as e:
            logger.exception("Unexpected LLM error for image %s", img_path)
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected LLM error for image {img_path.name}: {e}",
            )

        results.append(
            ImageResult(
                filename=img_path.name,
                raw_text=text,
                health_data=health_data,
            )
        )

    #Save to Postgres
    try:
        inserted_ids = save_results_to_db(folder_name, results)
        logger.info(
            "Saved %d rows to Postgres for folder_name=%s",
            len(inserted_ids),
            folder_name,
        )
    except Exception as e:
        logger.exception("Failed to save results to Postgres")
        raise HTTPException(
            status_code=500,
            detail=f"Error saving results to database: {e}",
        )

    return ProcessFolderResponse(
        folder_name=folder_name,
        images_processed=len(results),
        results=results,
    )


# @app.get("/export-folder/{folder_name}")
# def export_folder_to_excel(folder_name: str):
#     """
#     Export all records for a given folder_name from Postgres to an Excel file.
#     Returns the Excel file for download.
#     """
#     # Query DB
#     with get_db() as db:
#         rows = (
#             db.query(FitIn50Workout)
#             .filter(FitIn50Workout.folder_name == folder_name)
#             .order_by(FitIn50Workout.id.asc())
#             .all()
#         )
#
#     if not rows:
#         raise HTTPException(
#             status_code=404,
#             detail=f"No records found for folder_name={folder_name}",
#         )
#
#     # Build DataFrame
#     data = []
#     for r in rows:
#         data.append(
#             {
#                 "id": r.id,
#                 "folder_name": r.folder_name,
#                 "filename": r.filename,
#                 "steps": r.steps,
#                 "calories_kcal": r.calories_kcal,
#                 "distance_km": r.distance_km,
#                 "active_time_minutes": r.active_time_minutes,
#                 "workout_type": r.workout_type,
#                 "created_at": r.created_at,
#             }
#         )
#
#     df = pd.DataFrame(data)
#
#     # Create Excel file in a temp location
#     export_dir = Path(settings.DOWNLOAD_ROOT_DIR) / "exports"
#     export_dir.mkdir(parents=True, exist_ok=True)
#     excel_path = export_dir / f"{folder_name}.xlsx"
#
#     df.to_excel(excel_path, index=False, engine="openpyxl")
#
#     return FileResponse(
#         path=str(excel_path),
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         filename=f"{folder_name}.xlsx",
#     )
