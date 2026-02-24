"""
Shared Pydantic schemas for API serialization.

These schemas ensure compatibility between backend and frontend JSON serialization.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SetLog(BaseModel):
    """Single set performance - JSON serializable."""
    weight: float
    reps: int
    rpe: int = Field(ge=1, le=10, description="Rate of Perceived Exertion 1-10")

    class Config:
        json_schema_extra = {
            "example": {
                "weight": 225.0,
                "reps": 5,
                "rpe": 9
            }
        }


class ExerciseLog(BaseModel):
    """Logged performance for one exercise - JSON serializable."""
    exercise_name: str
    muscle_group: str
    sets: List[SetLog]
    average_rpe: float = 0.0

    class Config:
        json_schema_extra = {
            "example": {
                "exercise_name": "Squat",
                "muscle_group": "legs",
                "sets": [
                    {"weight": 225.0, "reps": 5, "rpe": 9}
                ],
                "average_rpe": 9.0
            }
        }


class WorkoutStateResponse(BaseModel):
    """API response model for workout state."""
    user_id: str
    selected_persona: Literal["iron", "yoga", "hiit", "kickboxing"]
    fatigue_scores: Dict[str, float]
    workouts_completed_this_week: int
    max_workouts_per_week: int
    fatigue_threshold: float
    daily_workout: Optional[Dict] = None
    is_working_out: Optional[bool] = False
    active_logs: Optional[List[Dict]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "selected_persona": "iron",
                "fatigue_scores": {"legs": 0.3, "push": 0.2},
                "workouts_completed_this_week": 2,
                "max_workouts_per_week": 4,
                "fatigue_threshold": 0.8,
                "daily_workout": None,
                "is_working_out": False,
                "active_logs": []
            }
        }
