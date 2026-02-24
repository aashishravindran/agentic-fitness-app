from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

# Load .env file if it exists
import config  # noqa: F401

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from llm import get_llm_model
from agents.retriever import RetrieverConfig, retrieve_creator_rules
from state import FitnessState


# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================


class Exercise(BaseModel):
    """Individual exercise in a workout."""

    exercise_name: str = Field(description="Name of the exercise (e.g., 'Barbell Back Squat')")
    sets: int = Field(description="Number of sets", ge=1, le=10)
    reps: str = Field(description="Rep range (e.g., '5', '8-10', 'AMRAP')")
    tempo_notes: str = Field(
        description="Tempo and execution notes (e.g., '3-second eccentrics, 1-second pause at bottom')"
    )
    iron_justification: str = Field(
        description="One-sentence explanation referencing Coach Iron's rules for why this exercise fits"
    )


class WorkoutPlan(BaseModel):
    """Complete workout plan with exercises and rationale."""

    focus_area: str = Field(description="Primary muscle group or movement pattern for today")
    total_exercises: int = Field(description="Number of exercises in the workout", ge=1, le=8)
    exercises: List[Exercise] = Field(description="List of exercises in order")
    fatigue_adaptations: Optional[str] = Field(
        default=None,
        description="Notes on how fatigue scores influenced exercise selection",
    )
    overall_rationale: str = Field(
        description="Brief summary of how this workout aligns with Coach Iron's philosophy"
    )


# ============================================================================
# Trainer Agent Configuration
# ============================================================================

# Iron Reasoning System Prompt
IRON_REASONING_PROMPT = """You are the AI Digital Twin of Coach Iron. You are disciplined, technical, and prioritize longevity over "ego lifting."

## Core Principles:

1. **Philosophy First**: Every workout MUST follow the rules in the retrieved_philosophy. If Iron says "3-second eccentrics," you must explicitly state that in the exercise notes.

2. **Fatigue Mitigation**: Check the fatigue_scores. If a muscle group is > 0.6 fatigued, you MUST:
   - Swap for a "Recovery-Aligned" movement (lower intensity, mobility-focused)
   - OR pivot to a different muscle group entirely
   - NEVER force heavy lifting when fatigue is high

3. **The "Iron Reasoning"**: For every exercise you suggest, provide a one-sentence justification (iron_justification) referencing Coach Iron's rules.

4. **Adaptation Logic**: If fatigue_scores show legs are tired (e.g., > 0.6) but Coach Iron's philosophy says today is 'Leg Power Day,' use your reasoning to suggest a modified lower-impact mobility session or active recovery instead of skipping it entirely.

5. **Output Format**: Always return structured JSON that a frontend can easily render. Be specific with tempo notes and rep ranges."""


# Trainer Agent (lazy-initialized to avoid import-time failures)
_trainer_agent: Agent | None = None


def get_trainer_agent() -> Agent:
    """Get or create the trainer agent (lazy initialization)."""
    global _trainer_agent
    if _trainer_agent is None:
        _trainer_agent = Agent(
            model=get_llm_model(),
            system_prompt=IRON_REASONING_PROMPT,
            result_type=WorkoutPlan,
            retries=3,  # Ollama/local models often need extra retries for structured output
        )
    return _trainer_agent


# ============================================================================
# LangGraph Node Function
# ============================================================================


async def trainer_node(state: FitnessState) -> Dict:
    """
    Trainer Agent node for LangGraph.
    
    Flow:
    1. Fetch philosophy from ChromaDB (if not already in state)
    2. Build context prompt with fatigue scores and philosophy
    3. Generate structured workout using PydanticAI
    4. Return updated state with daily_workout and retrieved_philosophy
    
    Args:
        state: FitnessState dict with user_id, selected_creator, fatigue_scores, etc.
    
    Returns:
        Dict with updated state fields: daily_workout, retrieved_philosophy
    """
    # 1. Fetch Philosophy (using retriever if not already in state)
    if not state.get("retrieved_philosophy") and state.get("retrieved_rules"):
        # Combine retrieved rules into a single philosophy string
        philosophy = "\n\n".join(state["retrieved_rules"])
    elif not state.get("retrieved_philosophy"):
        # Need to retrieve from ChromaDB
        persist_dir = Path(__file__).parents[1] / "creator_db"
        cfg = RetrieverConfig(
            persist_dir=persist_dir,
            collection_name="creator_rules",
        )
        rules = retrieve_creator_rules(
            query="Provide the complete training philosophy, rules, and programming principles.",
            selected_creator=state["selected_creator"],
            k=8,  # Get more context for full philosophy
            config=cfg,
        )
        philosophy = "\n\n".join(rules)
    else:
        philosophy = state["retrieved_philosophy"]

    # 2. Build the "Think" Prompt
    fatigue_str = ", ".join([f"{k}: {v:.2f}" for k, v in state["fatigue_scores"].items()])
    goal = state.get("goal", "General fitness and strength")
    
    # Identify high-fatigue muscle groups
    high_fatigue = [k for k, v in state["fatigue_scores"].items() if v > 0.6]
    fatigue_warning = ""
    if high_fatigue:
        fatigue_warning = f"\n\n⚠️ CRITICAL: The following muscle groups are highly fatigued (>0.6): {', '.join(high_fatigue)}. You MUST adapt the workout to avoid these areas or use recovery-aligned movements only."

    prompt = f"""Current Fatigue Scores: {fatigue_str}
{fatigue_warning}
Creator Rules (Coach Iron's Philosophy):
{philosophy}

User Goal: {goal}

Design a workout that respects these constraints. 
- If fatigue is high (>0.6) for a muscle group, pivot to a different movement or use recovery-aligned alternatives.
- Every exercise must explicitly reference Coach Iron's rules in the iron_justification field.
- Include specific tempo notes (e.g., "3-second eccentrics" if that's in the philosophy).
- Return a structured workout plan that a frontend can render as JSON."""

    # 3. Generate Structured Output using PydanticAI
    agent = get_trainer_agent()
    result = await agent.run(prompt)
    workout_plan = result.data

    # 4. Convert to JSON-friendly dict
    daily_workout = workout_plan.model_dump(mode="json")

    # Return updated state
    return {
        "daily_workout": daily_workout,
        "retrieved_philosophy": philosophy,
        "current_workout": workout_plan.model_dump_json(),  # Also keep string version for backward compat
    }


# ============================================================================
# Synchronous Wrapper (for testing without async)
# ============================================================================


def trainer_node_sync(state: FitnessState) -> Dict:
    """
    Synchronous wrapper for trainer_node. Useful for testing.
    Requires an event loop to be running.
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(trainer_node(state))
