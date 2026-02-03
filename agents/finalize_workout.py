"""
Finalize Workout Node (v1 Workout Logging)

Runs after the user has optionally logged sets (log-exercise). Appends the workout
to history, increments weekly counter, and applies RPE-based fatigue (or default).
"""

from __future__ import annotations

from typing import Dict, List

from state import FitnessState

# RPE-based fatigue deltas (replaces static +0.5)
FATIGUE_RPE_HIGH = 0.6   # RPE 8-10
FATIGUE_RPE_MID = 0.4    # RPE 5-7
FATIGUE_RPE_LOW = 0.2    # RPE < 5
DEFAULT_FATIGUE_INCREMENT = 0.5  # when no logs


def _rpe_to_fatigue_delta(rpe: float) -> float:
    """Map average RPE to fatigue increment."""
    if rpe >= 8:
        return FATIGUE_RPE_HIGH
    if rpe >= 5:
        return FATIGUE_RPE_MID
    return FATIGUE_RPE_LOW


def _fatigue_keys_for_workout(daily_workout: Dict) -> List[str]:
    """Primary fatigue_scores key(s) for this workout's focus (single key)."""
    keys: List[str] = []
    focus_area = (daily_workout.get("focus_area") or "").lower()
    focus_system = (daily_workout.get("focus_system") or "").lower()
    focus_attribute = (daily_workout.get("focus_attribute") or "").lower()
    if focus_area:
        if "leg" in focus_area or "squat" in focus_area or "deadlift" in focus_area:
            keys.append("legs")
        if "push" in focus_area or "chest" in focus_area or "press" in focus_area:
            keys.append("push")
        if "pull" in focus_area or "back" in focus_area or "row" in focus_area:
            keys.append("pull")
        if "spine" in focus_area:
            keys.append("spine")
        if "hip" in focus_area:
            keys.append("hips")
        if "shoulder" in focus_area:
            keys.append("shoulders")
    if focus_system:
        if "cardio" in focus_system or "metabolic" in focus_system:
            keys.append("cardio")
        if "cns" in focus_system:
            keys.append("cns")
    if focus_attribute:
        if "coordination" in focus_attribute:
            keys.append("coordination")
        if "speed" in focus_attribute or "power" in focus_attribute:
            keys.append("speed")
        if "endurance" in focus_attribute:
            keys.append("endurance")
    seen: set = set()
    out = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    if not out and focus_area:
        out = ["legs" if "leg" in focus_area else "push" if "push" in focus_area else "pull"]
    if not out and focus_system:
        out = ["cardio"]
    if not out and focus_attribute:
        out = ["coordination"]
    return out[:1]


def compute_fatigue_from_logs(
    current_fatigue: Dict[str, float],
    active_logs: List[Dict],
) -> Dict[str, float]:
    """
    Compute fatigue deltas from ExerciseLogs (RPE-based) and merge into current fatigue.
    Per exercise: average_rpe (or average of sets' rpe) -> delta; apply to muscle_group.
    """
    updated = dict(current_fatigue)
    for log in active_logs:
        muscle_group = (log.get("muscle_group") or "").strip().lower()
        if not muscle_group:
            continue
        sets_list = log.get("sets") or []
        if not sets_list:
            avg_rpe = log.get("average_rpe", 0.0)
        else:
            rpes = [s.get("rpe", 5) for s in sets_list if isinstance(s, dict)]
            avg_rpe = sum(rpes) / len(rpes) if rpes else 5.0
        delta = _rpe_to_fatigue_delta(avg_rpe)
        updated[muscle_group] = min(1.0, updated.get(muscle_group, 0.0) + delta)
    return updated


def compute_default_fatigue(
    current_fatigue: Dict[str, float],
    daily_workout: Dict,
) -> Dict[str, float]:
    """Apply default +0.5 to workout focus when no logs."""
    keys = _fatigue_keys_for_workout(daily_workout)
    updated = dict(current_fatigue)
    for k in keys:
        updated[k] = min(1.0, updated.get(k, 0.0) + DEFAULT_FATIGUE_INCREMENT)
    return updated


def finalize_workout_node(state: FitnessState) -> Dict:
    """
    Run after interrupt (user may have run log-exercise). Append workout to history,
    increment counter, apply RPE-based or default fatigue, clear active_logs.
    """
    daily_workout = state.get("daily_workout")
    if not daily_workout:
        return {
            "active_logs": [],
            "is_working_out": False,
        }
    history = list(state.get("workout_history", []))
    history.append(daily_workout)
    workouts_completed = state.get("workouts_completed_this_week", 0) + 1
    fatigue_scores = state.get("fatigue_scores", {})
    active_logs = state.get("active_logs") or []

    if active_logs:
        fatigue_scores = compute_fatigue_from_logs(fatigue_scores, active_logs)
    else:
        fatigue_scores = compute_default_fatigue(fatigue_scores, daily_workout)

    return {
        "workout_history": history,
        "workouts_completed_this_week": workouts_completed,
        "fatigue_scores": fatigue_scores,
        "active_logs": [],
        "is_working_out": False,
    }
