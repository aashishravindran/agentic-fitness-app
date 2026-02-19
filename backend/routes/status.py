"""
Status endpoints for user progress and fatigue tracking.
"""

import sys
from pathlib import Path

# Add backend directory to path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi import APIRouter, HTTPException
from services.workout_service import WorkoutService

router = APIRouter()


@router.get("/users/{user_id}/status")
async def get_user_status(user_id: str):
    """
    Get user's weekly progress and fatigue heatmap.
    
    Returns:
        - workouts_completed_this_week: int
        - max_workouts_per_week: int
        - fatigue_scores: Dict[str, float]
        - fatigue_threshold: float
        - selected_persona: str
    """
    try:
        workout_service = WorkoutService(user_id=user_id)
        state = await workout_service.get_current_state()
        
        if not state:
            # Return defaults for new user
            return {
                "workouts_completed_this_week": 0,
                "max_workouts_per_week": 4,
                "fatigue_scores": {},
                "fatigue_threshold": 0.8,
                "selected_persona": "iron",
                "subscribed_personas": [],
            }

        return {
            "workouts_completed_this_week": state.get("workouts_completed_this_week", 0),
            "max_workouts_per_week": state.get("max_workouts_per_week", 4),
            "fatigue_scores": state.get("fatigue_scores", {}),
            "fatigue_threshold": state.get("fatigue_threshold", 0.8),
            "selected_persona": state.get("selected_persona", "iron"),
            "subscribed_personas": state.get("subscribed_personas") or [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
