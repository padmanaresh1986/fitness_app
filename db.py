# db.py
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator, Iterable, List
import pandas as pd
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Text,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy import create_engine

from git_push import push_excel_to_github
from models import HealthData, ImageResult


from dotenv import load_dotenv
load_dotenv()

# Example: postgresql://user:password@localhost:5432/fitin50
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/fitin50",
)

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


class FitIn50Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    folder_name = Column(String(64), nullable=False)
    filename = Column(Text, nullable=False)
    email = Column(Text, nullable=False)
    steps = Column(Integer, nullable=True)
    calories_kcal = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)
    active_time_minutes = Column(Float, nullable=True)
    workout_type = Column(String(32), nullable=True)
    total_points = Column(Integer, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_tables() -> None:
    """
    Call once at startup if you want SQLAlchemy to ensure the table exists.
    (You can also manage schema manually with the SQL script.)
    """
    Base.metadata.create_all(bind=engine)


def save_results_to_db(
    folder_name: str,
    results: Iterable[ImageResult],
) -> List[int]:
    """
    Insert one row per ImageResult into fitin50_workouts.
    Returns list of inserted row IDs.
    """
    inserted_ids: List[int] = []

    excel_records: List[dict] = []  # ✅ dicts, not ORM objects

    # with get_db() as db:
    #     for r in results:
    #         h: HealthData = r.health_data
    #
    #         row = FitIn50Workout(
    #             folder_name=folder_name,
    #             filename=r.filename,
    #             email = r.filename.partition('_')[0],
    #             steps=h.steps,
    #             calories_kcal=h.calories_kcal,
    #             distance_km=h.distance_km,
    #             active_time_minutes=h.active_time_minutes,
    #             workout_type=h.workout_type,
    #             total_points=h.total_points,
    #         )
    #         db.add(row)
    #         db.flush()  # get primary key
    #         inserted_ids.append(row.id)
    #
    #         # ✅ Convert to dict WHILE SESSION IS OPEN
    #         excel_records.append({
    #             "folder_name": row.folder_name,
    #             "filename": row.filename,
    #             "email": row.email,
    #             "steps": row.steps,
    #             "calories_kcal": row.calories_kcal,
    #             "distance_km": row.distance_km,
    #             "active_time_minutes": row.active_time_minutes,
    #             "workout_type": row.workout_type,
    #             "total_points": row.total_points,
    #             "created_at": row.created_at,
    #         })
    #
    #     db.commit()  # ✅ IMPORTANT
    #
    for r in results:
        h: HealthData = r.health_data

        row = FitIn50Workout(
            folder_name=folder_name,
            filename=r.filename,
            email=r.filename.partition('_')[0],
            steps=h.steps,
            calories_kcal=h.calories_kcal,
            distance_km=h.distance_km,
            active_time_minutes=h.active_time_minutes,
            workout_type=h.workout_type,
            total_points=h.total_points,
        )

        # ✅ Convert to dict WHILE SESSION IS OPEN
        excel_records.append({
            "folder_name": row.folder_name,
            "filename": row.filename,
            "email": row.email,
            "steps": row.steps,
            "calories_kcal": row.calories_kcal,
            "distance_km": row.distance_km,
            "active_time_minutes": row.active_time_minutes,
            "workout_type": row.workout_type,
            "total_points": row.total_points,
            "created_at": row.created_at,
        })

    date_folder = folder_name

    excel_path, file_name = export_records_to_excel(excel_records, f"data/{date_folder}/")

    github_url = push_excel_to_github(
        local_file_path=excel_path,
        github_token=os.getenv("GITHUB_API_KEY"),
        owner="krishnasabbu",
        repo="fitness-challenge",
        repo_file_path=f"data/{date_folder}/{file_name}"
    )

    print("✅ Excel pushed to GitHub:", github_url)

    output_leader_folder = generate_leaderboard("data", f"data/{date_folder}")

    github_leaderboard_url = push_excel_to_github(
        local_file_path=output_leader_folder,
        github_token= os.getenv("GITHUB_API_KEY"),
        owner="krishnasabbu",
        repo="fitness-challenge",
        repo_file_path=f"data/{date_folder}/leaderboard.xlsx"
    )

    print("✅ Excel pushed to GitHub:", github_leaderboard_url)

    return inserted_ids


import os
import pandas as pd
import numpy as np
from datetime import datetime


def export_records_to_excel(records: list[dict], output_dir="."):
    """
    Sheet 1: Raw daily data
    Sheet 2: Grouped summary by email
    Returns: (file_path, file_name)
    """

    df = pd.DataFrame(records)

    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"fitness_data_{timestamp}.xlsx"
    file_path = os.path.join(output_dir, file_name)

    # -------------------------
    # Prepare summary sheet
    # -------------------------
    summary_df = (
        df.groupby("email", as_index=False)
        .agg({
            "steps": "max",  # highest steps per user
            "calories_kcal": "sum",
            "distance_km": "sum",
            "active_time_minutes": "sum",
            "total_points": "sum",  # base points
            "workout_type": lambda x: ", ".join(sorted(set(filter(None, x))))
        })
    )

    # -------------------------
    # Step points calculation
    # -------------------------
    summary_df["step_points"] = np.select(
        [
            summary_df["steps"] <= 5000,
            summary_df["steps"] <= 8000,
            summary_df["steps"] <= 10000,
            summary_df["steps"] <= 15000,
            summary_df["steps"] <= 20000,
        ],
        [25, 35, 80, 150, 300],
        default=500
    )

    # Add step points to total points
    summary_df["total_points"] += summary_df["step_points"]

    # Optional: remove step_points column from final output
    summary_df.drop(columns=["step_points"], inplace=True)

    # -------------------------
    # Rename columns for clarity
    # -------------------------
    summary_df.rename(columns={
        "steps": "total_steps",
        "calories_kcal": "total_calories_kcal",
        "distance_km": "total_distance_km",
        "active_time_minutes": "total_active_time_minutes",
        "workout_type": "workout_types"
    }, inplace=True)

    # -------------------------
    # Write Excel file
    # -------------------------
    with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Daily Data", index=False)
        summary_df.to_excel(writer, sheet_name="Daily Summary", index=False)

    return file_path, file_name



def generate_leaderboard(data_folder: str, output_folder: str):
    """
    Aggregate all daily summary sheets and create a leaderboard Excel.

    :param data_folder: Path containing date folders with daily Excel files.
    :param output_folder: Folder where the final 'leader_board.xls' will be saved.
    :return: Path to the saved leaderboard Excel file.
    """
    all_summary_dfs = []

    # Traverse all files in the data_folder (including date subfolders)
    for root, dirs, files in os.walk(data_folder):
        for file in files:
            if file.startswith("fitness") and file.endswith(".xlsx"):
                file_path = os.path.join(root, file)
                try:
                    # Read the Daily Summary sheet
                    df = pd.read_excel(file_path, sheet_name="Daily Summary")
                    all_summary_dfs.append(df)
                except Exception as e:
                    print(f"⚠️ Failed to read Daily Summary from {file_path}: {e}")

    if not all_summary_dfs:
        raise ValueError("No Daily Summary sheets found in the given data folder.")

    # Combine all summaries
    combined_df = pd.concat(all_summary_dfs, ignore_index=True)

    # Aggregate by email
    leaderboard_df = combined_df.groupby('email', as_index=False).agg({
        'total_steps': 'sum',
        'total_calories_kcal': 'sum',
        'total_distance_km': 'sum',
        'total_active_time_minutes': 'sum',
        'total_points': 'sum',
        'workout_types': lambda x: ", ".join(sorted(set(",".join(x).split(","))))
    })

    # Rank by total_points descending
    leaderboard_df = leaderboard_df.sort_values(by='total_points', ascending=False)
    leaderboard_df['rank'] = range(1, len(leaderboard_df) + 1)

    # Reorder columns
    cols = ['rank', 'email', 'total_steps', 'total_calories_kcal', 'total_distance_km',
            'total_active_time_minutes', 'total_points', 'workout_types']
    leaderboard_df = leaderboard_df[cols]

    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Save leaderboard Excel
    output_file = os.path.join(output_folder, "leader_board.xlsx")
    leaderboard_df.to_excel(output_file, index=False, sheet_name="Leaderboard")

    print(f"✅ Leaderboard Excel saved: {output_file}")
    return output_file