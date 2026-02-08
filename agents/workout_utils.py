"""
Shared utilities for workout processing.
"""

from __future__ import annotations

from typing import Any, Dict


def inject_exercise_ids(workout_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add an 'id' to each exercise/pose/activity in a workout for reliable logging.

    - Strength/HIIT/Kickboxing: exercises list -> id on each item
    - Yoga: poses list -> id on each item
    - Recovery: activities list -> id on each item

    IDs are stable within the workout: ex_0, ex_1, ...
    """
    if not workout_dict:
        return workout_dict

    # Strength, HIIT, Kickboxing
    exercises = workout_dict.get("exercises")
    if exercises and isinstance(exercises, list):
        for i, ex in enumerate(exercises):
            if isinstance(ex, dict):
                ex["id"] = f"ex_{i}"

    # Yoga
    poses = workout_dict.get("poses")
    if poses and isinstance(poses, list):
        for i, pose in enumerate(poses):
            if isinstance(pose, dict):
                pose["id"] = f"ex_{i}"

    # Recovery
    activities = workout_dict.get("activities")
    if activities and isinstance(activities, list):
        for i, act in enumerate(activities):
            if isinstance(act, dict):
                act["id"] = f"ex_{i}"

    return workout_dict
