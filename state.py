from __future__ import annotations

from typing import Dict, List, Literal, Optional, TypedDict


class FitnessState(TypedDict):
    # Identity & Routing
    user_id: str
    selected_persona: Literal["iron", "yoga", "hiit", "kickboxing"]
    selected_creator: str  # Legacy: kept for backward compatibility
    next_node: str  # Node to route to next (set by supervisor)
    
    # Persistent State
    fatigue_scores: Dict[str, float]  # e.g., {"legs": 0.8, "push": 0.1, "spine": 0.3}
    last_session_timestamp: float  # Unix timestamp of last session
    
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


