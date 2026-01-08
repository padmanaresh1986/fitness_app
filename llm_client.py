# llm_client.py

from __future__ import annotations

import json

import requests

from config import settings
from models import HealthData
from together import Together
import os

from dotenv import load_dotenv
load_dotenv()

class LLMExtractionError(Exception):
    pass


def build_extraction_prompt(text: str) -> str:
    """
    Ask the model to extract numeric metrics + workout_type.
    workout_type must be one of: sport, strength_training, cardio, yoga.
    If unsure, choose the closest category; use null only if absolutely no workout is implied.
    """
    return f"""
    Return ONLY valid JSON. No text, no markdown, no explanations.

    From the text below, extract the following fields:
    - steps (number, null if not available)
    - calories_kcal (number, null if not available)
    - distance_km (number, null if not available)
    - active_time_minutes (number, null if not available)
    - workout_type ("cardio", "sport", "strength_training", "yoga", or null)

    Workout_type rules:
    - "cardio": walk, run, treadmill, cycling, or generic workouts
    - "sport": games like cricket, football, basketball, tennis, etc.
    - "strength_training": gym, weights, resistance, bodyweight exercises
    - "yoga": yoga, stretching, meditation
    - null: if no workout described

    Text:
    {text}

    JSON ONLY. Example of correct format:

    {{
      "steps": 7672,
      "calories_kcal": null,
      "distance_km": 5.54,
      "active_time_minutes": 75.56,
      "workout_type": "cardio"
    }}
    """.strip()


def call_ollama(prompt: str) -> str:
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    print("Calling Ollama with prompt:")
    print(prompt)
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    # Ollama returns {"response": "..."} (maybe with newlines)
    raw = data.get("response", "")
    return raw.strip()


def call_togather_ai(prompt: str) -> str:
    client = Together(api_key=os.getenv("TOGETHER_API_KEY"))

    response = client.chat.completions.create(
        model="ServiceNow-AI/Apriel-1.6-15b-Thinker",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    print(response.choices[0].message.content)
    return response.choices[0].message.content.strip()


def parse_health_json(raw: str) -> HealthData:
    """
    Parse raw LLM output as JSON and coerce into HealthData.
    Tries to handle minor deviations gracefully.
    """
    # Some models may prepend or append junk; try to find first '{' and last '}'.
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or start > end:
        raise LLMExtractionError(f"Could not find JSON object in response: {raw[:200]}")

    json_str = raw[start : end + 1]

    try:
        obj = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise LLMExtractionError(f"Invalid JSON from LLM: {e} | raw={raw[:200]}") from e

    # Defensive conversion to correct types
    def to_int(v):
        if v is None:
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    def to_float(v):
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    def normalize_workout_type(v):
        if v is None:
            return None
        if not isinstance(v, str):
            return None
        v_norm = v.strip().lower()
        allowed = {"sport", "strength_training", "cardio", "yoga"}
        # map a few likely variants
        aliases = {
            "strength": "strength_training",
            "strength-training": "strength_training",
            "strength training": "strength_training",
        }
        if v_norm in aliases:
            v_norm = aliases[v_norm]
        return v_norm if v_norm in allowed else None

    health = HealthData(
        steps=to_int(obj.get("steps")),
        calories_kcal=to_float(obj.get("calories_kcal")),
        distance_km=to_float(obj.get("distance_km")),
        active_time_minutes=to_float(obj.get("active_time_minutes")),
        workout_type=normalize_workout_type(obj.get("workout_type")),
        total_points=calculate_points(to_int(obj.get("steps")), normalize_workout_type(obj.get("workout_type")))
    )
    return health


def extract_health_data_from_text(text: str) -> HealthData:
    prompt = build_extraction_prompt(text)
    #raw = call_ollama(prompt)
    raw = call_togather_ai(prompt)
    health = parse_health_json(raw)
    return health

def calculate_points(steps: int, workout_type: str) -> int:
    # Workout points mapping
    workout_points = {
        "sport": 300,                # Any Sport
        "strength_training": 300,    # Strength Training/HIIT
        "cardio": 200,               # Cardio
        "yoga": 200                  # Yoga
    }

    # Step points calculation
    if steps <= 5000:
        step_points = 25
    elif steps <= 8000:
        step_points = 35
    elif steps <= 10000:
        step_points = 80
    elif steps <= 15000:
        step_points = 150
    elif steps <= 20000:
        step_points = 300
    else:
        step_points = 500

    # Workout points (0 if no valid workout)
    workout_score = workout_points.get(workout_type, 0)

    return step_points + workout_score
