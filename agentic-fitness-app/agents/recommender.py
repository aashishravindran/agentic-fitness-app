"""
Persona Recommendation Engine

Stand-alone agentic node that suggests a fitness persona based on user biometrics
and goals. Only triggers for non-onboarded users or when re-evaluation is requested.

Uses dynamic discovery of creators/ directory to identify available personas.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, List, Optional

import config  # noqa: F401

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from llm import get_llm_model
from state import FitnessState

# Map creator keys (from creators/*.md stems) to persona keys (used by supervisor/workers)
CREATOR_TO_PERSONA = {
    "coach_iron": "iron",
    "zenflow_yoga": "yoga",
    "inferno_hiit": "hiit",
    "strikeforce_kb": "kickboxing",
}


class Recommendation(BaseModel):
    """Structured recommendation output (up to 2 personas + duration)."""
    suggested_personas: List[str] = Field(
        min_length=1,
        max_length=2,
        description="One or two creator keys that best match the user (e.g. ['coach_iron', 'zenflow_yoga'])"
    )
    suggested_duration_minutes: int = Field(
        ge=10,
        le=120,
        description="Recommended workout duration in minutes (e.g. 30, 45, 60). "
        "Consider the user's fitness level, goals, and any time constraints mentioned."
    )
    rationale: str = Field(
        description="A brief explanation for the recommendation"
    )


RECOMMENDER_PROMPT = """You are a Fitness Placement Expert.

Analyze the user's biometrics, goals, and fitness level against the available training philosophies.

Base your recommendations primarily on HIIT and yoga - they suit most users (weight loss, general fitness, flexibility, cardio, recovery):
- inferno_hiit: Cardiovascular capacity and metabolic health. High intensity, minimum time. Ideal for weight loss and cardio.
- zenflow_yoga: Flexibility, mobility, and recovery for all levels. Breath-first, movement as medicine. Ideal for flexibility, stress relief, and injury prevention.

Also available when strength or combat fitness is the primary goal:
- coach_iron: Strength and muscle mass for moderate/advanced users. Progressive overload, big lifts.
- strikeforce_kb: Combat fitness, coordination, speed, power, endurance. Technique over power.

Prioritize inferno_hiit and/or zenflow_yoga unless the user explicitly focuses on strength or combat. Return 1 or 2 creator keys as a list. Use exact names: coach_iron, zenflow_yoga, inferno_hiit, strikeforce_kb.

**Equipment constraint**: The user may list equipment they have available. Only recommend personas whose workouts are feasible with that equipment. For example, if the user only has a yoga mat and resistance bands, don't recommend coach_iron (needs barbell/dumbbells). If no equipment is specified, assume a well-equipped gym.

**Duration**: Also recommend a workout duration in minutes (10-120). Consider fitness level (beginners: 20-30min, intermediate: 30-45min, advanced: 45-60min), goals, and any time constraints the user mentioned."""


def discover_available_creators(creators_dir: Optional[Path] = None) -> List[str]:
    """Scan creators/ directory for available personas (*.md files)."""
    if creators_dir is None:
        creators_dir = Path(__file__).parents[1] / "creators"
    creators_dir = creators_dir.resolve()
    if not creators_dir.exists():
        return list(CREATOR_TO_PERSONA.keys())  # Fallback to known creators
    return [f.stem for f in creators_dir.glob("*.md")]


def get_recommender_agent() -> Agent:
    """Create the recommender agent."""
    return Agent(
        model=get_llm_model(),
        system_prompt=RECOMMENDER_PROMPT,
        result_type=Recommendation,
        retries=3,
    )


async def persona_recommendation_node_async(state: FitnessState) -> Dict:
    """
    Recommender node: suggests best-fit persona based on user metrics.

    Uses dynamic discovery of creators/ directory.
    Returns recommended_persona and sets is_onboarded=True.
    """
    creators_path = Path(__file__).parents[1] / "creators"
    available_creators = discover_available_creators(creators_path)

    height = state.get("height_cm")
    weight = state.get("weight_kg")
    goal = state.get("goal", "Improve fitness")
    fitness_level = state.get("fitness_level", "Intermediate")
    about_me = state.get("about_me") or ""
    equipment = state.get("equipment") or []

    context = (
        f"User Metrics: Height {height}cm, Weight {weight}kg. "
        f"Goal: {goal}. Fitness Level: {fitness_level}. "
    )
    if equipment:
        context += f"Available Equipment: {', '.join(equipment)}. Only recommend personas whose workouts work with this equipment. "
    if about_me:
        context += f"Personal context (use for hyper-personalized recommendation): {about_me}. "
    context += f"Available Personas: {', '.join(available_creators)}. Return 1 or 2 creator keys as a list."

    agent = get_recommender_agent()
    result = await agent.run(context)

    raw = result.data.suggested_personas
    suggested_list = raw if isinstance(raw, list) else ([raw] if raw else [])
    normalized: List[str] = []
    for s in suggested_list[:2]:  # Max 2
        if s in CREATOR_TO_PERSONA.values():
            s = next((c for c, p in CREATOR_TO_PERSONA.items() if p == s), s)
        elif s not in available_creators:
            s = available_creators[0] if available_creators else "coach_iron"
        if s and s not in normalized:
            normalized.append(s)
    if not normalized:
        normalized = [available_creators[0]] if available_creators else ["coach_iron"]

    primary = normalized[0]
    persona_keys = [CREATOR_TO_PERSONA.get(c, "iron") for c in normalized]
    rationale = result.data.rationale

    return {
        "recommended_personas": normalized,
        "recommended_persona": primary,  # Legacy: first recommended
        "recommendation_rationale": rationale,
        "subscribed_personas": persona_keys,
        "recommendation_pending": True,  # User must accept before is_onboarded=True
        "selected_persona": persona_keys[0],
        "selected_creator": primary,
        "workout_duration_minutes": result.data.suggested_duration_minutes,
    }


def persona_recommendation_node(state: FitnessState) -> Dict:
    """Synchronous wrapper for the recommender node."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(persona_recommendation_node_async(state))


# ---------------------------------------------------------------------------
# Refine recommendation: re-run with user feedback
# ---------------------------------------------------------------------------

REFINE_PROMPT = """You are a Fitness Placement Expert adapting a previous recommendation based on user feedback.

Available personas (use exact names):
- coach_iron: Strength and muscle mass. Progressive overload, big lifts.
- zenflow_yoga: Flexibility, mobility, recovery. Breath-first, movement as medicine.
- inferno_hiit: Cardiovascular capacity and metabolic health. High intensity, minimum time.
- strikeforce_kb: Combat fitness, coordination, speed, power, endurance.

Your previous recommendation is provided along with the user's feedback.
Adapt the recommendation to incorporate the user's preferences while still being appropriate for their profile.
Return 1 or 2 creator keys as a list. Use exact names: coach_iron, zenflow_yoga, inferno_hiit, strikeforce_kb.

The user may mention equipment they have — only recommend personas whose workouts are feasible with that equipment.
Also adapt the duration recommendation based on feedback (e.g. time constraints)."""


def _get_refine_agent() -> Agent:
    """Create the refine-recommendation agent."""
    return Agent(
        model=get_llm_model(),
        system_prompt=REFINE_PROMPT,
        result_type=Recommendation,
        retries=3,
    )


def _normalize_creators(raw_list: list, available_creators: List[str]) -> List[str]:
    """Normalize a list of creator/persona names to valid creator keys."""
    normalized: List[str] = []
    for s in raw_list[:2]:
        if s in CREATOR_TO_PERSONA.values():
            s = next((c for c, p in CREATOR_TO_PERSONA.items() if p == s), s)
        elif s not in available_creators:
            s = available_creators[0] if available_creators else "coach_iron"
        if s and s not in normalized:
            normalized.append(s)
    if not normalized:
        normalized = [available_creators[0]] if available_creators else ["coach_iron"]
    return normalized


async def refine_recommendation_async(state: FitnessState, feedback: str) -> Dict:
    """
    Re-run the recommender incorporating user feedback on the previous suggestion.

    Args:
        state: Current FitnessState (must have a previous recommendation).
        feedback: User's natural-language feedback (e.g. "I also want HIIT").

    Returns:
        Updated recommendation fields (same shape as persona_recommendation_node).
    """
    creators_path = Path(__file__).parents[1] / "creators"
    available_creators = discover_available_creators(creators_path)

    height = state.get("height_cm")
    weight = state.get("weight_kg")
    goal = state.get("goal", "Improve fitness")
    fitness_level = state.get("fitness_level", "Intermediate")
    about_me = state.get("about_me") or ""
    prev_personas = state.get("recommended_personas") or []
    prev_rationale = state.get("recommendation_rationale") or ""
    user_equipment = state.get("equipment") or []
    prev_duration = state.get("workout_duration_minutes")

    context = (
        f"User Metrics: Height {height}cm, Weight {weight}kg. "
        f"Goal: {goal}. Fitness Level: {fitness_level}. "
    )
    if user_equipment:
        context += f"Available Equipment: {', '.join(user_equipment)}. Only recommend personas whose workouts work with this equipment. "
    if about_me:
        context += f"Personal context: {about_me}. "
    context += (
        f"\nPrevious recommendation: {', '.join(prev_personas)}. "
        f"Previous rationale: {prev_rationale}. "
    )
    if prev_duration:
        context += f"Previous duration: {prev_duration} minutes. "
    context += (
        f"\nUser feedback: {feedback}. "
        f"\nAvailable Personas: {', '.join(available_creators)}. "
        f"Adapt the recommendation based on the user's feedback. Return 1 or 2 creator keys as a list."
    )

    agent = _get_refine_agent()
    result = await agent.run(context)

    normalized = _normalize_creators(
        result.data.suggested_personas if isinstance(result.data.suggested_personas, list)
        else [result.data.suggested_personas],
        available_creators,
    )
    primary = normalized[0]
    persona_keys = [CREATOR_TO_PERSONA.get(c, "iron") for c in normalized]

    return {
        "recommended_personas": normalized,
        "recommended_persona": primary,
        "recommendation_rationale": result.data.rationale,
        "subscribed_personas": persona_keys,
        "recommendation_pending": True,
        "selected_persona": persona_keys[0],
        "selected_creator": primary,
        "workout_duration_minutes": result.data.suggested_duration_minutes,
    }


def refine_recommendation(state: FitnessState, feedback: str) -> Dict:
    """Synchronous wrapper for refine_recommendation_async."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(refine_recommendation_async(state, feedback))
