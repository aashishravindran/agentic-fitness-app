"""
Onboarding and profile endpoints for persona recommendation.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db_utils import get_user_state, update_subscribed_personas, accept_recommendation
from feature_flags import ENABLE_PERSONA_RECOMMENDER
from graph import run_onboard, run_refine_recommendation

logger = logging.getLogger(__name__)
router = APIRouter()


class OnboardRequest(BaseModel):
    """Request body for POST /users/{id}/onboard."""
    height_cm: float = Field(..., gt=0, lt=300, description="User height in cm")
    weight_kg: float = Field(..., gt=0, lt=500, description="User weight in kg")
    goal: str = Field(..., min_length=1, description="User's fitness goal")
    fitness_level: str = Field(
        default="Intermediate",
        description="Beginner, Intermediate, or Advanced",
    )


class IntakeRequest(BaseModel):
    """Request body for POST /users/{id}/intake (SuperSet narrative intake)."""
    height_cm: Optional[float] = Field(default=None, ge=0, lt=300, description="User height in cm")
    weight_kg: Optional[float] = Field(default=None, ge=0, lt=500, description="User weight in kg")
    fitness_level: str = Field(
        default="Intermediate",
        description="Beginner, Intermediate, or Advanced",
    )
    about_me: str = Field(
        default="",
        description="Free-text narrative context (e.g., lifestyle, interests, limitations)",
    )
    equipment: Optional[List[str]] = Field(
        default=None,
        description="Equipment available to the user (e.g. ['dumbbells', 'pull-up bar', 'yoga mat'])",
    )


class SelectPersonasRequest(BaseModel):
    """Request body for POST /users/{id}/select-persona."""
    personas: List[str] = Field(
        ...,
        min_length=1,
        description="List of persona keys (iron, yoga, hiit, kickboxing) or creator keys to subscribe to"
    )


class RefineRecommendationRequest(BaseModel):
    """Request body for POST /users/{id}/refine-recommendation."""
    feedback: str = Field(
        ...,
        min_length=1,
        description="Natural-language feedback on the recommendation (e.g. 'I also want HIIT')",
    )


@router.post("/users/{user_id}/onboard")
async def onboard_user(user_id: str, body: OnboardRequest):
    """
    Submit biometric data and trigger the persona recommender.

    Returns the AI-suggested persona with rationale.
    Skips recommender if ENABLE_PERSONA_RECOMMENDER is False.
    """
    if not ENABLE_PERSONA_RECOMMENDER:
        raise HTTPException(
            status_code=501,
            detail="Persona recommender is disabled (ENABLE_PERSONA_RECOMMENDER=False)",
        )

    # User already onboarded - skip recommender
    existing = get_user_state(user_id)
    if existing and existing.get("is_onboarded"):
        raise HTTPException(
            status_code=409,
            detail="User already onboarded. Use GET /profile to view persona settings or select-persona to change.",
        )

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_onboard(
                user_id=user_id,
                height_cm=body.height_cm,
                weight_kg=body.weight_kg,
                goal=body.goal,
                fitness_level=body.fitness_level,
            ),
        )
        return {
            "recommended_personas": result.get("recommended_personas", []),
            "recommended_persona": result.get("recommended_persona"),  # Legacy: first
            "subscribed_personas": result.get("subscribed_personas", []),
            "selected_persona": result.get("selected_persona"),
            "rationale": result.get("recommendation_rationale", "Persona recommended based on your profile."),
            "recommendation_pending": True,
            "workout_duration_minutes": result.get("workout_duration_minutes"),
        }
    except Exception as e:
        logger.exception("Onboard failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/users/{user_id}/select-persona")
async def select_persona(user_id: str, body: SelectPersonasRequest):
    """
    Persist the user's subscribed personas to the database.
    User can subscribe to multiple personas (recommended + any additional).
    """
    success = update_subscribed_personas(user_id, body.personas)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="User not found. Complete onboarding first.",
        )
    return {"status": "ok", "subscribed_personas": body.personas}


@router.get("/users/{user_id}/profile")
async def get_profile(user_id: str):
    """
    Return stored biometric data and persona settings.
    """
    state = get_user_state(user_id)
    if not state:
        return {
            "user_id": user_id,
            "height_cm": None,
            "weight_kg": None,
            "fitness_level": None,
            "is_onboarded": False,
            "selected_persona": None,
            "subscribed_personas": [],
            "recommended_personas": [],
            "recommended_persona": None,
            "recommendation_rationale": None,
            "about_me": None,
            "equipment": None,
            "workout_duration_minutes": None,
        }

    return {
        "user_id": user_id,
        "height_cm": state.get("height_cm"),
        "weight_kg": state.get("weight_kg"),
        "fitness_level": state.get("fitness_level"),
        "is_onboarded": state.get("is_onboarded", False),
        "recommendation_pending": state.get("recommendation_pending", False),
        "selected_persona": state.get("selected_persona"),
        "subscribed_personas": state.get("subscribed_personas") or [],
        "recommended_personas": state.get("recommended_personas") or [],
        "recommended_persona": state.get("recommended_persona"),
        "recommendation_rationale": state.get("recommendation_rationale"),
        "about_me": state.get("about_me"),
        "equipment": state.get("equipment"),
        "workout_duration_minutes": state.get("workout_duration_minutes"),
    }


@router.post("/users/{user_id}/intake")
async def complete_intake(user_id: str, body: IntakeRequest):
    """
    SuperSet narrative intake: persist height, weight, fitness_level, about_me,
    run recommender with personal context, set is_onboarded=True.
    """
    if not ENABLE_PERSONA_RECOMMENDER:
        raise HTTPException(
            status_code=501,
            detail="Persona recommender is disabled (ENABLE_PERSONA_RECOMMENDER=False)",
        )
    existing = get_user_state(user_id)
    if existing and existing.get("is_onboarded"):
        raise HTTPException(status_code=409, detail="User already onboarded.")

    try:
        from graph import run_intake
        from db_utils import _save_state_to_checkpoint, get_user_state as _get_state

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_intake(
                user_id=user_id,
                height_cm=body.height_cm,
                weight_kg=body.weight_kg,
                fitness_level=body.fitness_level,
                about_me=body.about_me or "",
            ),
        )
        # Persist equipment if provided (user input, not AI output)
        if body.equipment is not None:
            st = _get_state(user_id)
            if st:
                st["equipment"] = body.equipment
                _save_state_to_checkpoint(user_id, st)
        return {
            "status": "ok",
            "recommendation_pending": True,
            "recommended_personas": result.get("recommended_personas", []),
            "subscribed_personas": result.get("subscribed_personas", []),
            "rationale": result.get("recommendation_rationale", ""),
            "workout_duration_minutes": result.get("workout_duration_minutes"),
            "equipment": body.equipment,
        }
    except Exception as e:
        logger.exception("Intake failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/users/{user_id}/refine-recommendation")
async def refine_recommendation(user_id: str, body: RefineRecommendationRequest):
    """
    Re-run the recommender incorporating user feedback on the previous suggestion.

    Only works when a recommendation is pending (after onboard/intake, before accept).
    Returns updated recommendation for the user to review.
    """
    if not ENABLE_PERSONA_RECOMMENDER:
        raise HTTPException(
            status_code=501,
            detail="Persona recommender is disabled (ENABLE_PERSONA_RECOMMENDER=False)",
        )

    existing = get_user_state(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found. Complete onboarding first.")

    if existing.get("is_onboarded") and not existing.get("recommendation_pending"):
        raise HTTPException(
            status_code=409,
            detail="User already onboarded. No pending recommendation to refine.",
        )

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_refine_recommendation(
                user_id=user_id,
                feedback=body.feedback,
            ),
        )
        return {
            "recommended_personas": result.get("recommended_personas", []),
            "recommended_persona": result.get("recommended_persona"),
            "subscribed_personas": result.get("subscribed_personas", []),
            "selected_persona": result.get("selected_persona"),
            "rationale": result.get("recommendation_rationale", ""),
            "recommendation_pending": True,
            "workout_duration_minutes": result.get("workout_duration_minutes"),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Refine recommendation failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/users/{user_id}/accept-recommendation")
async def accept_recommendation_endpoint(user_id: str):
    """
    Accept the current pending recommendation and finalize onboarding.

    Sets is_onboarded=True and clears recommendation_pending.
    """
    existing = get_user_state(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found. Complete onboarding first.")

    if existing.get("is_onboarded") and not existing.get("recommendation_pending"):
        raise HTTPException(status_code=409, detail="User already onboarded. No pending recommendation.")

    if not existing.get("recommended_personas"):
        raise HTTPException(
            status_code=400,
            detail="No recommendation to accept. Run onboarding first.",
        )

    state = accept_recommendation(user_id)
    if not state:
        raise HTTPException(status_code=500, detail="Failed to accept recommendation.")

    return {
        "status": "ok",
        "is_onboarded": True,
        "selected_persona": state.get("selected_persona"),
        "subscribed_personas": state.get("subscribed_personas") or [],
        "recommended_personas": state.get("recommended_personas") or [],
        "rationale": state.get("recommendation_rationale", ""),
        "equipment": state.get("equipment"),
        "workout_duration_minutes": state.get("workout_duration_minutes"),
    }
