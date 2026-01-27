"""
Specialist Worker Nodes

Each worker is a specialized trainer agent that:
1. Retrieves their specific creator philosophy from RAG
2. Generates workouts tailored to their domain
3. Returns structured WorkoutPlan
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

# Load .env file if it exists
import config  # noqa: F401

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from agents.retriever import RetrieverConfig, retrieve_creator_rules
from agents.trainer import get_llm_model
from state import FitnessState

# Import models (same as trainer.py)
GoogleModel = None
OpenAIModel = None
OllamaModel = None

try:
    from pydantic_ai.models.google import GoogleModel
except ImportError:
    try:
        from pydantic_ai.models.gemini import GeminiModel as GoogleModel
    except ImportError:
        GoogleModel = None

try:
    from pydantic_ai.models.openai import OpenAIModel
except ImportError:
    OpenAIModel = None

try:
    from pydantic_ai.models.ollama import OllamaModel
except ImportError:
    OllamaModel = None


# ============================================================================
# Pydantic Models for Different Workout Types
# ============================================================================


class StrengthExercise(BaseModel):
    """Exercise for strength training (Iron, some Kickboxing)."""
    exercise_name: str
    sets: int = Field(ge=1, le=10)
    reps: str  # e.g., "5", "8-10", "AMRAP"
    tempo_notes: str
    iron_justification: str


class YogaExercise(BaseModel):
    """Exercise for yoga (ZenFlow)."""
    pose_name: str
    duration: str  # e.g., "30 seconds", "2 minutes", "5 breaths"
    modifications: Optional[str] = None
    focus_area: str  # "spine", "hips", "shoulders"
    zen_justification: str


class HIITExercise(BaseModel):
    """Exercise for HIIT (Inferno)."""
    exercise_name: str
    work_duration: str  # e.g., "30 seconds", "1 minute"
    rest_duration: str
    intensity_zone: str  # "Zone 2", "Zone 4", "Zone 5"
    rounds: int = Field(ge=1, le=20)
    inferno_justification: str


class KickboxingExercise(BaseModel):
    """Exercise for kickboxing (Strikeforce)."""
    exercise_name: str
    round_duration: str  # e.g., "3 minutes", "2 minutes"
    rest_duration: str
    intensity: str  # "Technical", "Moderate", "High", "Peak"
    focus: str  # "coordination", "speed", "power", "endurance"
    rounds: int = Field(ge=1, le=12)
    strikeforce_justification: str


class StrengthWorkoutPlan(BaseModel):
    """Workout plan for strength training."""
    focus_area: str
    total_exercises: int = Field(ge=1, le=8)
    exercises: List[StrengthExercise]
    fatigue_adaptations: Optional[str] = None
    overall_rationale: str


class YogaWorkoutPlan(BaseModel):
    """Workout plan for yoga."""
    focus_area: str  # "spine", "hips", "shoulders", or combination
    total_poses: int = Field(ge=1, le=15)
    total_duration: str  # e.g., "45 minutes"
    poses: List[YogaExercise]
    fatigue_adaptations: Optional[str] = None
    overall_rationale: str


class HIITWorkoutPlan(BaseModel):
    """Workout plan for HIIT."""
    focus_system: str  # "cardio", "cns", "metabolic", or combination
    total_exercises: int = Field(ge=1, le=10)
    total_duration: str
    exercises: List[HIITExercise]
    fatigue_adaptations: Optional[str] = None
    overall_rationale: str


class KickboxingWorkoutPlan(BaseModel):
    """Workout plan for kickboxing."""
    focus_attribute: str  # "coordination", "speed", "power", "endurance"
    total_exercises: int = Field(ge=1, le=8)
    total_duration: str
    exercises: List[KickboxingExercise]
    fatigue_adaptations: Optional[str] = None
    overall_rationale: str


# ============================================================================
# Worker Base Class
# ============================================================================


def get_worker_agent(result_type: type, system_prompt: str) -> Agent:
    """Create a worker agent with specified result type and prompt."""
    return Agent(
        model=get_llm_model(),
        system_prompt=system_prompt,
        result_type=result_type,
    )


def retrieve_worker_philosophy(creator_name: str, k: int = 8) -> str:
    """Retrieve philosophy for a specific creator."""
    persist_dir = Path(__file__).parents[1] / "creator_db"
    cfg = RetrieverConfig(
        persist_dir=persist_dir,
        collection_name="creator_rules",
    )
    rules = retrieve_creator_rules(
        query="Provide the complete training philosophy, rules, and programming principles.",
        selected_creator=creator_name,
        k=k,
        config=cfg,
    )
    return "\n\n".join(rules)


# ============================================================================
# Iron Worker (Strength Training)
# ============================================================================

IRON_PROMPT = """You are the Iron Worker, specialized in strength training.

Target Areas: push, pull, legs
Philosophy: Progressive overload, big lifts, controlled tempo.

Generate workouts that:
- Focus on push/pull/legs patterns
- Use sets and reps (not duration)
- Include tempo notes (e.g., "3-second eccentrics")
- Reference Coach Iron's rules in justifications
- Adapt when fatigue > 0.6 for target muscle groups"""


def iron_worker(state: FitnessState) -> Dict:
    """Iron Worker: Strength training specialist."""
    philosophy = retrieve_worker_philosophy("coach_iron")
    fatigue_scores = state.get("fatigue_scores", {})
    goal = state.get("goal", "Build strength")
    
    # Build prompt
    fatigue_str = ", ".join([f"{k}: {v:.2f}" for k, v in fatigue_scores.items()])
    high_fatigue = [k for k, v in fatigue_scores.items() if v > 0.6]
    warning = f"\n⚠️ High fatigue (>0.6): {', '.join(high_fatigue)}" if high_fatigue else ""
    
    prompt = f"""Fatigue Scores: {fatigue_str}{warning}
Goal: {goal}
Coach Iron's Philosophy:
{philosophy}

Generate a strength training workout focusing on push/pull/legs."""
    
    import asyncio
    
    agent = get_worker_agent(StrengthWorkoutPlan, IRON_PROMPT)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    result = loop.run_until_complete(agent.run(prompt))
    workout = result.data
    workout_dict = workout.model_dump(mode="json")
    
    # Update workout history - append this workout
    history = state.get("workout_history", [])
    history.append(workout_dict)
    
    # Increment weekly workout counter
    workouts_completed = state.get("workouts_completed_this_week", 0)
    
    return {
        "daily_workout": workout_dict,
        "active_philosophy": philosophy,
        "current_workout": workout.model_dump_json(),
        "workout_history": history,  # Save updated history
        "workouts_completed_this_week": workouts_completed + 1,  # Increment counter
    }


# ============================================================================
# Yoga Worker (Mobility)
# ============================================================================

YOGA_PROMPT = """You are the Yoga Worker, specialized in mobility and mindful movement.

Target Areas: spine, hips, shoulders
Philosophy: Movement as medicine, breath first, listen to your body.

Generate workouts that:
- Focus on spine/hips/shoulders
- Use duration (not sets/reps)
- Include modifications for different levels
- Reference ZenFlow's philosophy in justifications
- Adapt when fatigue > 0.6 for target areas"""


def yoga_worker(state: FitnessState) -> Dict:
    """Yoga Worker: Mobility specialist."""
    philosophy = retrieve_worker_philosophy("zenflow_yoga")
    fatigue_scores = state.get("fatigue_scores", {})
    goal = state.get("goal", "Improve mobility and flexibility")
    
    fatigue_str = ", ".join([f"{k}: {v:.2f}" for k, v in fatigue_scores.items()])
    high_fatigue = [k for k, v in fatigue_scores.items() if v > 0.6]
    warning = f"\n⚠️ High fatigue (>0.6): {', '.join(high_fatigue)}" if high_fatigue else ""
    
    prompt = f"""Fatigue Scores: {fatigue_str}{warning}
Goal: {goal}
ZenFlow Yoga Philosophy:
{philosophy}

Generate a yoga practice focusing on spine/hips/shoulders."""
    
    import asyncio
    
    agent = get_worker_agent(YogaWorkoutPlan, YOGA_PROMPT)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    result = loop.run_until_complete(agent.run(prompt))
    workout = result.data
    workout_dict = workout.model_dump(mode="json")
    
    # Update workout history - append this workout
    history = state.get("workout_history", [])
    history.append(workout_dict)
    
    # Increment weekly workout counter
    workouts_completed = state.get("workouts_completed_this_week", 0)
    
    return {
        "daily_workout": workout_dict,
        "active_philosophy": philosophy,
        "current_workout": workout.model_dump_json(),
        "workout_history": history,  # Save updated history
        "workouts_completed_this_week": workouts_completed + 1,  # Increment counter
    }


# ============================================================================
# HIIT Worker (Cardio)
# ============================================================================

HIIT_PROMPT = """You are the HIIT Worker, specialized in high-intensity interval training.

Target Systems: cardio, cns (central nervous system)
Philosophy: Maximum effort, minimum time, recovery is training.

Generate workouts that:
- Focus on cardio/cns systems
- Use work/rest intervals
- Specify intensity zones (Zone 2-5)
- Reference Inferno HIIT's philosophy in justifications
- Adapt when fatigue > 0.6 for cardio/cns"""


def hiit_worker(state: FitnessState) -> Dict:
    """HIIT Worker: Cardio specialist."""
    philosophy = retrieve_worker_philosophy("inferno_hiit")
    fatigue_scores = state.get("fatigue_scores", {})
    goal = state.get("goal", "Improve cardiovascular fitness")
    
    fatigue_str = ", ".join([f"{k}: {v:.2f}" for k, v in fatigue_scores.items()])
    high_fatigue = [k for k, v in fatigue_scores.items() if v > 0.6]
    warning = f"\n⚠️ High fatigue (>0.6): {', '.join(high_fatigue)}" if high_fatigue else ""
    
    prompt = f"""Fatigue Scores: {fatigue_str}{warning}
Goal: {goal}
Inferno HIIT Philosophy:
{philosophy}

Generate a HIIT workout focusing on cardio/cns systems."""
    
    import asyncio
    
    agent = get_worker_agent(HIITWorkoutPlan, HIIT_PROMPT)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    result = loop.run_until_complete(agent.run(prompt))
    workout = result.data
    workout_dict = workout.model_dump(mode="json")
    
    # Update workout history - append this workout
    history = state.get("workout_history", [])
    history.append(workout_dict)
    
    # Increment weekly workout counter
    workouts_completed = state.get("workouts_completed_this_week", 0)
    
    return {
        "daily_workout": workout_dict,
        "active_philosophy": philosophy,
        "current_workout": workout.model_dump_json(),
        "workout_history": history,  # Save updated history
        "workouts_completed_this_week": workouts_completed + 1,  # Increment counter
    }


# ============================================================================
# Kickboxing Worker (Coordination)
# ============================================================================

KB_PROMPT = """You are the Kickboxing Worker, specialized in combat fitness.

Target Attributes: coordination, speed, power, endurance
Philosophy: Technique over power, conditioning is king, mental toughness.

Generate workouts that:
- Focus on coordination/speed/power/endurance
- Use round-based structure (work/rest)
- Specify intensity levels (Technical/Moderate/High/Peak)
- Reference Strikeforce's philosophy in justifications
- Adapt when fatigue > 0.6 for target attributes"""


def kb_worker(state: FitnessState) -> Dict:
    """Kickboxing Worker: Combat fitness specialist."""
    philosophy = retrieve_worker_philosophy("strikeforce_kb")
    fatigue_scores = state.get("fatigue_scores", {})
    goal = state.get("goal", "Improve combat fitness and coordination")
    
    fatigue_str = ", ".join([f"{k}: {v:.2f}" for k, v in fatigue_scores.items()])
    high_fatigue = [k for k, v in fatigue_scores.items() if v > 0.6]
    warning = f"\n⚠️ High fatigue (>0.6): {', '.join(high_fatigue)}" if high_fatigue else ""
    
    prompt = f"""Fatigue Scores: {fatigue_str}{warning}
Goal: {goal}
Strikeforce Kickboxing Philosophy:
{philosophy}

Generate a kickboxing workout focusing on coordination/speed/power/endurance."""
    
    import asyncio
    
    agent = get_worker_agent(KickboxingWorkoutPlan, KB_PROMPT)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    result = loop.run_until_complete(agent.run(prompt))
    workout = result.data
    workout_dict = workout.model_dump(mode="json")
    
    # Update workout history - append this workout
    history = state.get("workout_history", [])
    history.append(workout_dict)
    
    # Increment weekly workout counter
    workouts_completed = state.get("workouts_completed_this_week", 0)
    
    return {
        "daily_workout": workout_dict,
        "active_philosophy": philosophy,
        "current_workout": workout.model_dump_json(),
        "workout_history": history,  # Save updated history
        "workouts_completed_this_week": workouts_completed + 1,  # Increment counter
    }
