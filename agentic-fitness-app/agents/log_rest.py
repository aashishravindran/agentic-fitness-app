"""
Log Rest Node

Handles logging rest days, which reduces fatigue scores to simulate recovery.
A rest day provides more aggressive fatigue reduction than time-based decay alone.
"""

from __future__ import annotations

import time
from typing import Dict

from state import FitnessState

# Rest day fatigue reduction factors
REST_REDUCTION_FACTOR = 0.7  # Reduce fatigue by 30% (multiply by 0.7)
# This means: fatigue_new = fatigue_old * 0.7
# Example: 0.8 fatigue → 0.56 fatigue after rest day


def log_rest_node(state: FitnessState) -> Dict:
    """
    Log a rest day and apply fatigue reduction.
    
    A rest day provides more aggressive recovery than time-based decay.
    This simulates the benefits of active rest, sleep, nutrition, etc.
    
    Args:
        state: FitnessState with fatigue_scores
    
    Returns:
        Updated state with reduced fatigue_scores and updated timestamp
    """
    current_time = time.time()
    fatigue_scores = state.get("fatigue_scores", {})
    
    # Apply rest day fatigue reduction to all muscle groups
    reduced_scores = {}
    for muscle_group, fatigue in fatigue_scores.items():
        # Apply reduction factor (30% reduction)
        new_fatigue = fatigue * REST_REDUCTION_FACTOR
        # Ensure it doesn't go below 0
        reduced_scores[muscle_group] = max(0.0, new_fatigue)
    
    # Update timestamp to current time (rest day counts as a session)
    # This ensures decay calculations work correctly going forward
    
    return {
        "fatigue_scores": reduced_scores,
        "last_session_timestamp": current_time,
    }
