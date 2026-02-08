"""
Settings endpoints for user preferences.
"""

import sys
from pathlib import Path

# Add backend directory to path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.workout_service import WorkoutService

router = APIRouter()


class SettingsUpdate(BaseModel):
    """Settings update payload."""
    max_workouts_per_week: int | None = None
    fatigue_threshold: float | None = None
    about_me: str | None = None


@router.patch("/users/{user_id}/settings")
async def update_user_settings(user_id: str, settings: SettingsUpdate):
    """
    Update user settings.
    
    Args:
        - max_workouts_per_week: Optional[int] - Maximum workouts per week
        - fatigue_threshold: Optional[float] - Fatigue threshold (0.0 to 1.0)
    
    Returns:
        Updated state
    """
    try:
        workout_service = WorkoutService(user_id=user_id)
        
        updates = {}
        if settings.max_workouts_per_week is not None:
            updates["max_workouts_per_week"] = settings.max_workouts_per_week
        if settings.about_me is not None:
            updates["about_me"] = settings.about_me
        if settings.fatigue_threshold is not None:
            if not 0.0 <= settings.fatigue_threshold <= 1.0:
                raise HTTPException(
                    status_code=400,
                    detail="fatigue_threshold must be between 0.0 and 1.0"
                )
            updates["fatigue_threshold"] = settings.fatigue_threshold
        
        if not updates:
            # No updates provided, return current state
            state = await workout_service.get_current_state()
            return state or {}
        
        # Update state
        updated_state = await workout_service.update_settings(updates)
        
        return updated_state
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
