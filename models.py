# models.py
from typing import List, Optional

from pydantic import BaseModel, Field


class HealthData(BaseModel):
    steps: Optional[int] = Field(None, description="Number of steps")
    calories_kcal: Optional[float] = Field(None, description="Calories in kcal")
    distance_km: Optional[float] = Field(None, description="Distance in kilometers")
    active_time_minutes: Optional[float] = Field(None, description="Active time in minutes")
    total_points: Optional[int] = Field(None, description="Total points earned")
    workout_type: Optional[str] = Field(
        None,
        description="Workout category: sport | strength_training | cardio | yoga",
    )


class ImageResult(BaseModel):
    filename: str
    raw_text: str
    health_data: HealthData


class ProcessFolderRequest(BaseModel):
    folder_name: str = Field(
        ...,
        description="Local folder name under Google Drive Desktop (e.g. 06-01-2026)",
    )


class ProcessFolderResponse(BaseModel):
    folder_name: str
    images_processed: int
    results: List[ImageResult]
