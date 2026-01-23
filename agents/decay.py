"""
Fatigue Decay Node

This node must run FIRST in the graph. It calculates time-based fatigue decay
based on hours passed since last_session_timestamp.

Formula: fatigue_new = fatigue_old * (decay_factor ^ hours_passed)
- After 24 hours: ~50% reduction
- After 48 hours: ~75% reduction
- After 72 hours: ~87% reduction
"""

from __future__ import annotations

import time
from typing import Dict

from state import FitnessState


def decay_node(state: FitnessState) -> Dict:
    """
    Apply time-based fatigue decay to all muscle groups.
    
    This node should run FIRST in the graph to ensure fatigue scores
    are up-to-date before routing decisions.
    
    Args:
        state: FitnessState with fatigue_scores and last_session_timestamp
    
    Returns:
        Updated state with decayed fatigue_scores and updated timestamp
    """
    current_time = time.time()
    last_session = state.get("last_session_timestamp", current_time)
    
    # Calculate hours passed
    hours_passed = (current_time - last_session) / 3600.0
    
    # Decay factor: 0.97 per hour (3% reduction per hour)
    # This means:
    # - After 24 hours: 0.97^24 ≈ 0.48 (52% reduction)
    # - After 48 hours: 0.97^48 ≈ 0.23 (77% reduction)
    # - After 72 hours: 0.97^72 ≈ 0.11 (89% reduction)
    decay_factor = 0.97
    
    # Apply decay to all fatigue scores
    decayed_scores = {}
    for muscle_group, fatigue in state.get("fatigue_scores", {}).items():
        # Apply exponential decay
        new_fatigue = fatigue * (decay_factor ** hours_passed)
        # Ensure it doesn't go below 0
        decayed_scores[muscle_group] = max(0.0, new_fatigue)
    
    # Update state
    return {
        "fatigue_scores": decayed_scores,
        "last_session_timestamp": current_time,
    }
