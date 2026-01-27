"""
History Analysis Node

Analyzes the last workout in history and applies a fatigue 'pre-load' based on
the intensity and volume of the previous day's workout.
"""

from __future__ import annotations

from typing import Dict

from state import FitnessState


def history_analysis_node(state: FitnessState) -> Dict:
    """
    Analyze the last workout in history and apply a fatigue 'pre-load'.
    
    This node runs after DecayNode to add fatigue based on the previous workout.
    Logic:
    - If the last workout targeted a muscle group, add fatigue (e.g., +0.3)
    - Fatigue is capped at 1.0
    - Different workout types map to different fatigue groups
    
    Args:
        state: FitnessState with workout_history and current fatigue_scores
    
    Returns:
        Updated state with fatigue_scores adjusted based on history
    """
    history = state.get("workout_history", [])
    if not history:
        # No history, return current fatigue unchanged
        return {"fatigue_scores": state.get("fatigue_scores", {})}

    # Get the most recent workout
    last_workout = history[-1]
    updated_fatigue = {**state.get("fatigue_scores", {})}
    
    # Extract focus area from the workout
    focus = last_workout.get("focus_area", "").lower()
    focus_attribute = last_workout.get("focus_attribute", "").lower()  # For kickboxing
    
    # Map workout focus to fatigue groups and apply penalties
    # Strength training (Iron, some Kickboxing)
    if "legs" in focus or "leg" in focus or "squat" in focus or "deadlift" in focus:
        updated_fatigue["legs"] = min(1.0, updated_fatigue.get("legs", 0.0) + 0.3)
    
    if "push" in focus or "chest" in focus or "shoulder" in focus or "press" in focus:
        updated_fatigue["push"] = min(1.0, updated_fatigue.get("push", 0.0) + 0.3)
    
    if "pull" in focus or "back" in focus or "row" in focus or "lat" in focus:
        updated_fatigue["pull"] = min(1.0, updated_fatigue.get("pull", 0.0) + 0.3)
    
    # Yoga/Mobility (spine, hips, shoulders)
    if "spine" in focus or "back" in focus or "spinal" in focus:
        updated_fatigue["spine"] = min(1.0, updated_fatigue.get("spine", 0.0) + 0.25)
    
    if "hips" in focus or "hip" in focus or "pelvis" in focus:
        updated_fatigue["hips"] = min(1.0, updated_fatigue.get("hips", 0.0) + 0.25)
    
    if "shoulder" in focus or "shoulders" in focus:
        updated_fatigue["shoulders"] = min(1.0, updated_fatigue.get("shoulders", 0.0) + 0.25)
    
    # HIIT/Cardio
    if "cardio" in focus or "hiit" in focus or "interval" in focus:
        updated_fatigue["cardio"] = min(1.0, updated_fatigue.get("cardio", 0.0) + 0.4)
        updated_fatigue["cns"] = min(1.0, updated_fatigue.get("cns", 0.0) + 0.3)
    
    # Kickboxing/Combat (coordination, speed, power, endurance)
    if "coordination" in focus_attribute or "coordination" in focus:
        updated_fatigue["coordination"] = min(1.0, updated_fatigue.get("coordination", 0.0) + 0.3)
    
    if "speed" in focus_attribute or "speed" in focus:
        updated_fatigue["speed"] = min(1.0, updated_fatigue.get("speed", 0.0) + 0.3)
    
    if "endurance" in focus_attribute or "endurance" in focus:
        updated_fatigue["endurance"] = min(1.0, updated_fatigue.get("endurance", 0.0) + 0.3)
        updated_fatigue["cardio"] = min(1.0, updated_fatigue.get("cardio", 0.0) + 0.2)
    
    # Check exercises for additional fatigue signals
    exercises = last_workout.get("exercises", [])
    for exercise in exercises:
        exercise_name = exercise.get("exercise_name", "").lower() or exercise.get("pose_name", "").lower()
        
        # Leg exercises
        if any(term in exercise_name for term in ["squat", "deadlift", "lunge", "leg press", "leg curl"]):
            updated_fatigue["legs"] = min(1.0, updated_fatigue.get("legs", 0.0) + 0.2)
        
        # Push exercises
        if any(term in exercise_name for term in ["bench", "press", "push-up", "shoulder press", "dip"]):
            updated_fatigue["push"] = min(1.0, updated_fatigue.get("push", 0.0) + 0.2)
        
        # Pull exercises
        if any(term in exercise_name for term in ["row", "pull-up", "lat", "chin-up", "pull"]):
            updated_fatigue["pull"] = min(1.0, updated_fatigue.get("pull", 0.0) + 0.2)
        
        # High intensity indicators
        if any(term in exercise_name for term in ["sprint", "burpee", "jump", "explosive"]):
            updated_fatigue["cns"] = min(1.0, updated_fatigue.get("cns", 0.0) + 0.15)

    return {"fatigue_scores": updated_fatigue}
