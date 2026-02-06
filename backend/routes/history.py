"""
History endpoints for workout history retrieval.
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


@router.get("/users/{user_id}/history")
async def get_user_history(user_id: str):
    """
    Get user's workout history from persistent storage.
    
    Returns:
        - workout_history: List[Dict] - List of previous workout JSONs
    """
    try:
        workout_service = WorkoutService(user_id=user_id)
        state = await workout_service.get_current_state()
        
        if not state:
            return {"workout_history": []}
        
        return {
            "workout_history": state.get("workout_history", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
