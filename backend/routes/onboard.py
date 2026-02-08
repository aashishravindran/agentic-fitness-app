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

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db_utils import get_user_state, update_subscribed_personas
from feature_flags import ENABLE_PERSONA_RECOMMENDER
from graph import run_onboard

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


class SelectPersonasRequest(BaseModel):
    """Request body for POST /users/{id}/select-persona."""
    personas: List[str] = Field(
        ...,
        min_length=1,
        description="List of persona keys (iron, yoga, hiit, kickboxing) or creator keys to subscribe to"
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
        }

    return {
        "user_id": user_id,
        "height_cm": state.get("height_cm"),
        "weight_kg": state.get("weight_kg"),
        "fitness_level": state.get("fitness_level"),
        "is_onboarded": state.get("is_onboarded", False),
        "selected_persona": state.get("selected_persona"),
        "subscribed_personas": state.get("subscribed_personas") or [],
        "recommended_personas": state.get("recommended_personas") or [],
        "recommended_persona": state.get("recommended_persona"),
        "recommendation_rationale": state.get("recommendation_rationale"),
    }
