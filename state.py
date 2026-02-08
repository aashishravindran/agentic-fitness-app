from __future__ import annotations

from typing import Dict, List, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


# --- Workout logging (v1) ---
class SetLog(BaseModel):
    """Single set performance."""
    weight: float
    reps: int
    rpe: int = Field(ge=1, le=10, description="Rate of Perceived Exertion 1-10")


class ExerciseLog(BaseModel):
    """Logged performance for one exercise."""
    exercise_name: str
    muscle_group: str
    sets: List[SetLog]
    average_rpe: float = 0.0


class FitnessState(TypedDict):
    # Identity & Routing
    user_id: str
    selected_persona: Literal["iron", "yoga", "hiit", "kickboxing"]
    selected_creator: str  # Legacy: kept for backward compatibility
    next_node: str  # Node to route to next (set by supervisor)

    # Biometric & Onboarding
    height_cm: Optional[float]
    weight_kg: Optional[float]
    fitness_level: Optional[str]  # e.g., "Beginner", "Intermediate", "Advanced"
    is_onboarded: bool  # If True, recommender is skipped during standard workflows
    recommended_personas: Optional[List[str]]  # Up to 2 AI-suggested personas (creator keys)
    recommended_persona: Optional[str]  # Legacy: first of recommended_personas
    recommendation_rationale: Optional[str]  # Brief explanation for the recommendation
    subscribed_personas: Optional[List[str]]  # Personas user has subscribed to (can be multiple)

    # Persistent State
    fatigue_scores: Dict[str, float]  # e.g., {"legs": 0.8, "push": 0.1, "spine": 0.3}
    last_session_timestamp: float  # Unix timestamp of last session
    workout_history: List[Dict]  # Stores previous workout JSONs for history-based fatigue
    
    # Safety & Frequency Constraints
    max_workouts_per_week: int  # User's target frequency (default: 4)
    workouts_completed_this_week: int  # Counter for sessions in current period
    fatigue_threshold: float  # Score at which recovery becomes mandatory (default: 0.8)
    
    # Context
    messages: List[Dict[str, str]]  # Conversation history
    active_philosophy: Optional[str]  # Context pulled from RAG
    retrieved_rules: List[str]  # Context from RAG (chunks) - legacy
    retrieved_philosophy: str  # Combined philosophy text - legacy
    
    # Workout Output
    goal: str  # User's fitness goal
    current_workout: Optional[str]  # Legacy: string representation
    daily_workout: Optional[Dict]  # Structured workout plan (JSON-friendly)
    is_approved: bool  # HITL status

    # Live workout logging (v1)
    active_logs: Optional[List[Dict]]  # List of ExerciseLog as dicts (set after log-exercise)
    is_working_out: Optional[bool]  # True when paused after worker, waiting for log/finish


