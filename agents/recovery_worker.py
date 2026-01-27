"""
Recovery Worker Node

Specialized worker for rest days, active recovery, and recovery from high fatigue.
Provides "permission to rest" and suggests restorative activities.
"""

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from agents.trainer import get_llm_model
from state import FitnessState

# Load .env file if it exists
import config  # noqa: F401


class RecoveryActivity(BaseModel):
    """Single recovery activity recommendation."""
    activity_name: str = Field(description="Name of the recovery activity")
    activity_type: str = Field(
        description="Type: 'passive' (rest/sleep), 'active' (walking/mobility), or 'neat' (light movement)"
    )
    duration: str = Field(description="Duration, e.g., '20 minutes', '30 minutes', 'full day'")
    intensity: str = Field(description="Intensity level: 'Very Light', 'Light', 'Minimal'")
    rationale: str = Field(description="Why this activity helps recovery")


class RecoveryPlan(BaseModel):
    """Recovery plan for rest/recovery days."""
    recovery_focus: str = Field(description="Primary recovery goal, e.g., 'CNS Recovery', 'Muscle Repair', 'Total Rest'")
    total_activities: int = Field(ge=1, le=5, description="Number of recovery activities")
    activities: list[RecoveryActivity] = Field(description="List of recovery activities")
    step_goal: Optional[int] = Field(
        default=None,
        description="Optional NEAT step goal (e.g., 4000-6000 steps) for light movement"
    )
    permission_to_rest: str = Field(
        description="A supportive message giving the user permission to rest without guilt"
    )
    overall_rationale: str = Field(description="Why this recovery plan is appropriate given current fatigue levels")


RECOVERY_PROMPT = """You are the Recovery Coach, specialized in rest, recovery, and preventing overtraining.

Your goal is to ensure the user returns to their next session stronger. If they are overtrained, your job is to give them "Permission to Rest."

**Recovery Logic:**
- **Extreme Fatigue (any score > 0.8)**: Recommend Passive Recovery (sleep, hydration, total rest, minimal movement)
- **Moderate Fatigue (0.6-0.8)**: Recommend Active Recovery (20-30 min walk, gentle yoga flow, foam rolling, light stretching)
- **Mild Fatigue (< 0.6)**: Recommend NEAT activities (fun movement like playing a sport, dancing, or hitting 4,000-6,000 steps)

**NEAT Focus**: Suggest hitting a specific "light" step goal (e.g., 4,000–6,000 steps) to keep blood circulating without adding strain.

**Never suggest:**
- Weights or resistance training
- High-intensity cardio
- Structured workouts
- Anything that increases cortisol

**Always include:**
- A "permission to rest" message to reduce user guilt
- Rationale explaining why rest is the most productive thing right now
- Activities that lower cortisol (nature walks, foam rolling, gentle mobility)

Generate a recovery plan that helps the user recover and return stronger."""


def get_recovery_agent() -> Agent:
    """Get or create recovery agent."""
    return Agent(
        model=get_llm_model(),
        system_prompt=RECOVERY_PROMPT,
        result_type=RecoveryPlan,
    )


def recovery_worker(state: FitnessState) -> Dict:
    """
    Recovery Worker: Rest and recovery specialist.
    
    Handles:
    - High fatigue recovery
    - Weekly rest days
    - Active recovery recommendations
    - Permission to rest messaging
    
    Args:
        state: FitnessState with fatigue_scores and workout_history
    
    Returns:
        Updated state with recovery_workout plan
    """
    fatigue_scores = state.get("fatigue_scores", {})
    goal = state.get("goal", "Recover and return stronger")
    
    # Determine recovery intensity based on max fatigue
    max_fatigue = max(fatigue_scores.values()) if fatigue_scores else 0.0
    fatigue_str = ", ".join([f"{k}: {v:.2f}" for k, v in fatigue_scores.items()])
    
    if max_fatigue > 0.8:
        recovery_type = "extreme"
        recovery_note = "⚠️ Extreme fatigue detected - Passive recovery recommended"
    elif max_fatigue > 0.6:
        recovery_type = "moderate"
        recovery_note = "⚠️ Moderate fatigue - Active recovery recommended"
    else:
        recovery_type = "mild"
        recovery_note = "💚 Light fatigue - NEAT activities recommended"
    
    prompt = f"""Fatigue Scores: {fatigue_str}
{recovery_note}
Max Fatigue: {max_fatigue:.2f}
Recovery Type: {recovery_type}
Goal: {goal}

Generate a recovery plan appropriate for the current fatigue levels.
Focus on activities that promote recovery, reduce cortisol, and prepare the user for their next training session."""

    import asyncio
    
    agent = get_recovery_agent()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    result = loop.run_until_complete(agent.run(prompt))
    recovery_plan = result.data
    recovery_dict = recovery_plan.model_dump(mode="json")
    
    # Update workout history - append this recovery session
    history = state.get("workout_history", [])
    history.append(recovery_dict)
    
    # Recovery sessions don't count toward weekly workout limit
    # (They're rest days, not training days)
    workouts_completed = state.get("workouts_completed_this_week", 0)
    
    return {
        "daily_workout": recovery_dict,
        "active_philosophy": "Recovery is training. Rest is productive.",
        "current_workout": recovery_plan.model_dump_json(),
        "workout_history": history,  # Save updated history
        "workouts_completed_this_week": workouts_completed,  # Don't increment for recovery
    }
