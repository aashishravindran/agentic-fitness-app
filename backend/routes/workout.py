"""
Workout generation REST API.

Triggers the graph to generate a workout from a prompt.
"""

import sys
from pathlib import Path

# Add project root to path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db_utils import get_user_state
from services.workout_service import WorkoutService

router = APIRouter()


class GenerateWorkoutRequest(BaseModel):
    """Request body for POST /users/{id}/workout."""
    prompt: str = Field(..., min_length=1, description="Natural language prompt, e.g. 'I want a leg workout'")
    goal: Optional[str] = Field(
        default=None,
        description="User's fitness goal. If omitted, uses goal from profile.",
    )
    max_workouts_per_week: Optional[int] = Field(default=None, ge=1, le=7)


@router.post("/users/{user_id}/workout")
async def generate_workout(user_id: str, body: GenerateWorkoutRequest):
    """
    Trigger the graph to generate a workout from a prompt.

    Uses persona from profile (onboarding). User must be onboarded with at least one selected persona.
    """
    profile = get_user_state(user_id)
    if not profile:
        raise HTTPException(
            status_code=400,
            detail="User not found. Complete onboarding first: POST /api/users/{user_id}/onboard",
        )
    if not profile.get("is_onboarded"):
        raise HTTPException(
            status_code=400,
            detail="User must complete onboarding first: POST /api/users/{user_id}/onboard",
        )

    # subscribed_personas is source of truth (from select-persona API)
    subscribed = profile.get("subscribed_personas") or []
    persona = subscribed[0] if subscribed else profile.get("selected_persona")
    if not persona:
        raise HTTPException(
            status_code=400,
            detail="No persona selected. Select personas: POST /api/users/{user_id}/select-persona with body {\"personas\": [\"iron\", \"yoga\", ...]}",
        )

    goal = body.goal or profile.get("goal") or "Build strength and improve fitness"

    try:
        workout_service = WorkoutService(user_id=user_id)
        result = await workout_service.process_user_input(
            content=body.prompt,
            persona=persona,
            goal=goal,
            max_workouts_per_week=body.max_workouts_per_week,
            subscribed_personas=subscribed,
        )
        return {
            "workout": result.get("daily_workout"),
            "state": {
                "subscribed_personas": result.get("subscribed_personas") or subscribed,
                "selected_persona": result.get("selected_persona"),
                "goal": result.get("goal"),
                "fatigue_scores": result.get("fatigue_scores"),
                "is_working_out": result.get("is_working_out"),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/users/{user_id}/reset-fatigue")
async def reset_fatigue(user_id: str):
    """Reset fatigue scores to default (all low)."""
    try:
        workout_service = WorkoutService(user_id=user_id)
        result = await workout_service.reset_fatigue_scores()
        return result or {"status": "ok", "fatigue_scores": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/users/{user_id}/reset-workouts")
async def reset_workouts(user_id: str):
    """Reset workouts_completed_this_week to 0."""
    try:
        workout_service = WorkoutService(user_id=user_id)
        result = await workout_service.reset_workouts_completed()
        return result or {"status": "ok", "workouts_completed_this_week": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/users/{user_id}/new-week")
async def new_week(user_id: str):
    """Simulate new week: reset workouts counter and set last_session to 7 days ago (triggers decay on next run)."""
    from db_utils import simulate_new_week
    success = simulate_new_week(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "ok", "message": "New week simulated. Fatigue decay will apply on next workout."}


class LogSetRequest(BaseModel):
    """Request body for POST /users/{id}/log-set."""
    exercise: Optional[str] = Field(default=None, min_length=1, description="Exercise name (alternative to exercise_id)")
    exercise_id: Optional[str] = Field(default=None, min_length=1, description="Exercise ID from workout (e.g. ex_0, ex_1) - preferred for reliable matching")
    weight: float = Field(default=0.0, ge=0, description="Weight used (kg)")
    reps: int = Field(default=0, ge=0, description="Reps performed")
    rpe: int = Field(default=5, ge=1, le=10, description="Rate of perceived exertion 1-10")


@router.post("/users/{user_id}/log-set")
async def log_set(user_id: str, body: LogSetRequest):
    """
    Log a set for an exercise in the current workout.
    Call after generating a workout; can be called multiple times.
    Use exercise_id (e.g. ex_0, ex_1) for reliable matching, or exercise name.
    """
    if not body.exercise_id and not body.exercise:
        raise HTTPException(
            status_code=400,
            detail="Provide either exercise_id or exercise (name) to log a set.",
        )
    try:
        workout_service = WorkoutService(user_id=user_id)
        result = await workout_service.log_set(
            exercise_name=body.exercise,
            exercise_id=body.exercise_id,
            weight=body.weight,
            reps=body.reps,
            rpe=body.rpe,
        )
        return {
            "state": result,
            "workout": result.get("daily_workout"),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/users/{user_id}/finish-workout")
async def finish_workout(user_id: str):
    """
    Finish the current workout session.
    Resumes the graph, runs finalize_workout (applies fatigue, saves to history).
    """
    try:
        workout_service = WorkoutService(user_id=user_id)
        result = await workout_service.finish_workout()
        return {
            "state": result,
            "workout": None,
            "workout_completed": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
