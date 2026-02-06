"""
Workout Service Layer

Handles integration between FastAPI and LangGraph workout system.
Manages state persistence, graph execution, and interrupt handling.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List, Literal, Optional

# Add project root to path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config  # Load .env
from graph import build_graph
from state import FitnessState

logger = logging.getLogger(__name__)


class WorkoutService:
    """Service for managing workout sessions with LangGraph."""
    
    def __init__(self, user_id: str, checkpoint_dir: str = "checkpoints"):
        self.user_id = user_id
        self.checkpoint_dir = checkpoint_dir
        self._app = None
        self._config = {"configurable": {"thread_id": user_id}}
    
    @property
    def app(self):
        """Lazy load the compiled graph."""
        if self._app is None:
            self._app = build_graph(self.checkpoint_dir, enable_persistence=True)
        return self._app
    
    async def get_current_state(self) -> Optional[Dict]:
        """Get the current state from the checkpoint."""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            state_snapshot = await loop.run_in_executor(
                None,
                lambda: self.app.get_state(self._config)
            )
            
            if state_snapshot:
                values = getattr(state_snapshot, "values", state_snapshot)
                if isinstance(values, dict):
                    return values
                return getattr(values, "__dict__", {}) or {}
            return None
        except Exception as e:
            logger.error(f"Error getting state for user {self.user_id}: {e}")
            return None
    
    async def process_user_input(
        self,
        content: str,
        persona: Literal["iron", "yoga", "hiit", "kickboxing"] = "iron",
        goal: str = "Build strength and improve fitness",
    ) -> Dict:
        """
        Process user input and run the workout graph.
        
        This handles the initial state setup and graph execution.
        The graph will interrupt after worker nodes, waiting for user logging.
        """
        from graph import run_workout
        
        # Get current state to extract fatigue scores
        current_state = await self.get_current_state()
        
        # Default fatigue scores
        defaults = {
            "legs": 0.2, "push": 0.2, "pull": 0.2,
            "spine": 0.1, "hips": 0.1, "shoulders": 0.1,
            "cardio": 0.1, "cns": 0.1,
            "coordination": 0.1, "speed": 0.1, "endurance": 0.1,
        }
        
        # Use existing fatigue scores or defaults
        if current_state and current_state.get("fatigue_scores"):
            fatigue_scores = {**defaults, **current_state.get("fatigue_scores", {})}
        else:
            fatigue_scores = defaults
        
        # Build messages list
        messages = []
        if current_state and current_state.get("messages"):
            messages = list(current_state.get("messages", []))
        messages.append({"role": "user", "content": content})
        
        # Use run_workout which handles state loading and merging properly
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: run_workout(
                    user_id=self.user_id,
                    persona=persona,
                    goal=goal,
                    fatigue_scores=fatigue_scores,
                    messages=messages,
                    checkpoint_dir=self.checkpoint_dir,
                )
            )
            return result
        except Exception as e:
            logger.error(f"Error processing user input: {e}", exc_info=True)
            raise
    
    async def log_set(
        self,
        exercise_name: str,
        weight: float = 0.0,
        reps: int = 0,
        rpe: int = 5,
    ) -> Dict:
        """
        Log a set for an exercise.
        
        Updates the active_logs in state and returns updated state.
        """
        state = await self.get_current_state()
        if not state:
            raise ValueError("No active workout session")
        
        workout = state.get("daily_workout")
        if not workout:
            raise ValueError("No active workout")
        
        # Infer default muscle group from workout focus
        focus = (
            workout.get("focus_area") or
            workout.get("focus_system") or
            workout.get("focus_attribute") or
            "general"
        ).lower()
        
        default_muscle = "general"
        if "leg" in focus:
            default_muscle = "legs"
        elif "push" in focus or "chest" in focus:
            default_muscle = "push"
        elif "pull" in focus or "back" in focus:
            default_muscle = "pull"
        elif "spine" in focus:
            default_muscle = "spine"
        elif "hip" in focus:
            default_muscle = "hips"
        elif "shoulder" in focus:
            default_muscle = "shoulders"
        elif "cardio" in focus:
            default_muscle = "cardio"
        elif "cns" in focus:
            default_muscle = "cns"
        
        # Update active_logs
        active_logs = list(state.get("active_logs", []))
        found = False
        
        for entry in active_logs:
            if (entry.get("exercise_name") or "").strip().lower() == exercise_name.strip().lower():
                sets_list = entry.get("sets", [])
                sets_list.append({"weight": weight, "reps": reps, "rpe": rpe})
                entry["sets"] = sets_list
                entry["average_rpe"] = round(
                    sum(s.get("rpe", 5) for s in sets_list) / len(sets_list), 2
                )
                found = True
                break
        
        if not found:
            active_logs.append({
                "exercise_name": exercise_name.strip(),
                "muscle_group": default_muscle,
                "sets": [{"weight": weight, "reps": reps, "rpe": rpe}],
                "average_rpe": float(rpe),
            })
        
        # Update state
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.app.update_state(self._config, {"active_logs": active_logs})
        )
        
        # Return updated state
        return await self.get_current_state()
    
    async def approve_suggestion(self, approved: bool) -> Dict:
        """
        Handle approval/rejection of agent suggestions.
        
        For now, this just updates is_approved flag.
        Future: Could trigger graph resume with approval decision.
        """
        state = await self.get_current_state()
        if not state:
            raise ValueError("No active session")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.app.update_state(self._config, {"is_approved": approved})
        )
        
        return await self.get_current_state()
    
    async def resume_graph(self) -> Dict:
        """
        Resume the graph after interruption.
        
        This is called when the user wants to continue after logging sets.
        """
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.app.invoke(None, self._config)
            )
            return result
        except Exception as e:
            logger.error(f"Error resuming graph: {e}", exc_info=True)
            raise
    
    async def finish_workout(self) -> Dict:
        """
        Finish the current workout session.
        
        This resumes the graph to finalize_workout node, which applies RPE-based fatigue
        and saves the workout to history.
        """
        return await self.resume_graph()
    
    async def update_settings(self, updates: Dict) -> Dict:
        """
        Update user settings (max_workouts_per_week, fatigue_threshold).
        
        Args:
            updates: Dict with settings to update
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.app.update_state(self._config, updates)
        )
        
        return await self.get_current_state()
    
    async def reset_user_state(self) -> bool:
        """
        Reset/delete user state to start fresh.
        
        This deletes all checkpoints for the user, effectively starting from scratch.
        """
        try:
            from db_utils import delete_user
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: delete_user(self.user_id, self.checkpoint_dir)
            )
            return result
        except Exception as e:
            logger.error(f"Error resetting user state for {self.user_id}: {e}", exc_info=True)
            return False
    
    async def reset_fatigue_scores(self) -> Dict:
        """
        Reset fatigue scores to default values (all zeros or minimal defaults) for this user.
        
        This preserves workout history and other state, only resetting fatigue.
        The reset is scoped to the current user (self.user_id) via the checkpoint config.
        
        Returns:
            Updated state dict for this user
        """
        # Default fatigue scores (all low/zero)
        defaults = {
            "legs": 0.0, "push": 0.0, "pull": 0.0,
            "spine": 0.0, "hips": 0.0, "shoulders": 0.0,
            "cardio": 0.0, "cns": 0.0,
            "coordination": 0.0, "speed": 0.0, "endurance": 0.0,
        }
        
        # Update state with reset fatigue scores for this user
        # self._config contains {"configurable": {"thread_id": self.user_id}}
        # which ensures the update only affects this user's state
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.app.update_state(self._config, {"fatigue_scores": defaults})
        )
        
        # Return updated state for this user
        return await self.get_current_state()
    
    async def reset_workouts_completed(self) -> Dict:
        """
        Reset workouts_completed_this_week counter to zero for this user.
        
        This preserves workout history and other state, only resetting the weekly counter.
        Useful for starting a new week or resetting progress tracking.
        
        Returns:
            Updated state dict for this user
        """
        # Reset workouts completed to zero
        # self._config contains {"configurable": {"thread_id": self.user_id}}
        # which ensures the update only affects this user's state
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.app.update_state(self._config, {"workouts_completed_this_week": 0})
        )
        
        # Return updated state for this user
        return await self.get_current_state()
    
    async def log_rest_day(self) -> Dict:
        """
        Log a rest day and apply fatigue reduction for this user.
        
        Uses the graph system to properly log rest day through the checkpoint system.
        A rest day provides more aggressive recovery than time-based decay.
        Reduces all fatigue scores by 30% (multiplies by 0.7).
        
        Returns:
            Updated state dict with reduced fatigue scores
        """
        from graph import log_rest_day as graph_log_rest
        
        # Use graph.log_rest_day which properly handles state through the graph system
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: graph_log_rest(
                user_id=self.user_id,
                checkpoint_dir=self.checkpoint_dir,
            )
        )
        
        return result
