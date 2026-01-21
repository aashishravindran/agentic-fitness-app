from __future__ import annotations

from typing import Dict, List, Optional, TypedDict


class FitnessState(TypedDict):
    user_id: str
    selected_creator: str
    fatigue_scores: Dict[str, float]  # e.g., {"legs": 0.8, "push": 0.1}
    retrieved_rules: List[str]  # Context from RAG
    current_workout: Optional[str]
    is_approved: bool  # HITL status


