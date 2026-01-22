from __future__ import annotations

from typing import Dict, List, Optional, TypedDict


class FitnessState(TypedDict):
    user_id: str
    selected_creator: str
    goal: str  # User's fitness goal
    fatigue_scores: Dict[str, float]  # e.g., {"legs": 0.8, "push": 0.1}
    retrieved_rules: List[str]  # Context from RAG (chunks)
    retrieved_philosophy: str  # Combined philosophy text from creator
    current_workout: Optional[str]  # Legacy: string representation
    daily_workout: Optional[Dict]  # Structured workout plan (JSON-friendly)
    is_approved: bool  # HITL status


