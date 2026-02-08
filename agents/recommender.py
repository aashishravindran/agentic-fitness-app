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
    """Structured recommendation output (up to 2 personas)."""
    suggested_personas: List[str] = Field(
        min_length=1,
        max_length=2,
        description="One or two creator keys that best match the user (e.g. ['coach_iron', 'zenflow_yoga'])"
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

Prioritize inferno_hiit and/or zenflow_yoga unless the user explicitly focuses on strength or combat. Return 1 or 2 creator keys as a list. Use exact names: coach_iron, zenflow_yoga, inferno_hiit, strikeforce_kb."""


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

    context = (
        f"User Metrics: Height {height}cm, Weight {weight}kg. "
        f"Goal: {goal}. Fitness Level: {fitness_level}. "
        f"Available Personas: {', '.join(available_creators)}. "
        f"Return 1 or 2 creator keys as a list."
    )

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
        "subscribed_personas": persona_keys,  # User subscribes to recommended (can add more via API)
        "is_onboarded": True,
        "selected_persona": persona_keys[0],
        "selected_creator": primary,
    }


def persona_recommendation_node(state: FitnessState) -> Dict:
    """Synchronous wrapper for the recommender node."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(persona_recommendation_node_async(state))
