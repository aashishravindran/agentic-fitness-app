"""
LangGraph Workflow for Hierarchical Multi-Agent Fitness System

Flow:
1. Supervisor Node (entry point - handles user interactions, routing decision)
2. Decay Node (fatigue decay based on time - runs automatically)
3. History Analysis Node (applies fatigue based on previous workout)
4. Worker Node (specialized workout generation)
5. End

The Supervisor is the primary entry point for all user interactions.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal

from langgraph.graph import END, StateGraph

# Try importing SqliteSaver (optional - graph works without it)
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    SQLITE_AVAILABLE = True
except ImportError:
    SqliteSaver = None
    SQLITE_AVAILABLE = False

from agents.decay import decay_node
from agents.finalize_workout import finalize_workout_node
from agents.history_analyzer import history_analysis_node
from agents.log_rest import log_rest_node
from agents.recovery_worker import recovery_worker
from agents.supervisor import supervisor_node
from agents.workers import hiit_worker, iron_worker, kb_worker, yoga_worker
from state import FitnessState


def route_after_supervisor(state: FitnessState) -> Literal["iron_worker", "yoga_worker", "hiit_worker", "kb_worker", "recovery_worker", "end"]:
    """
    Route after Decay + History Analysis. Re-apply safety overrides using current state,
    since History Analysis may have pushed fatigue over threshold (supervisor saw stale fatigue).
    """
    # Safety override 1: weekly limit (use current state after decay/history)
    workouts_completed = state.get("workouts_completed_this_week", 0)
    max_workouts = state.get("max_workouts_per_week", 4)
    if workouts_completed >= max_workouts:
        return "end"

    # Safety override 2: fatigue threshold (fatigue may be higher after history_analysis)
    fatigue_scores = state.get("fatigue_scores", {})
    fatigue_threshold = state.get("fatigue_threshold", 0.8)
    max_fatigue = max(fatigue_scores.values()) if fatigue_scores else 0.0
    if max_fatigue > fatigue_threshold:
        return "recovery_worker"

    # Use supervisor's decision otherwise
    next_node = state.get("next_node", "end")
    return next_node


def build_graph(checkpoint_dir: str = "checkpoints", enable_persistence: bool = True):
    """
    Build the LangGraph workflow with optional persistence.
    
    Args:
        checkpoint_dir: Directory for SqliteSaver persistence
        enable_persistence: Whether to enable SQLite persistence
    
    Returns:
        Compiled StateGraph ready to run
    """
    # Create graph
    workflow = StateGraph(FitnessState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)  # Entry point for user interactions
    workflow.add_node("decay", decay_node)  # Runs automatically after supervisor
    workflow.add_node("history_analysis", history_analysis_node)  # Apply history-based fatigue
    workflow.add_node("iron_worker", iron_worker)
    workflow.add_node("yoga_worker", yoga_worker)
    workflow.add_node("hiit_worker", hiit_worker)
    workflow.add_node("kb_worker", kb_worker)
    workflow.add_node("recovery_worker", recovery_worker)
    workflow.add_node("finalize_workout", finalize_workout_node)  # v1: after log, apply RPE fatigue

    # Set entry point - Supervisor handles all user interactions
    workflow.set_entry_point("supervisor")
    
    # Flow: Supervisor → Decay → History Analysis → Route to worker
    workflow.add_edge("supervisor", "decay")
    workflow.add_edge("decay", "history_analysis")
    workflow.add_conditional_edges(
        "history_analysis",  # Route from history analysis
        route_after_supervisor,  # Route based on supervisor's next_node decision
        {
            "iron_worker": "iron_worker",
            "yoga_worker": "yoga_worker",
            "hiit_worker": "hiit_worker",
            "kb_worker": "kb_worker",
            "recovery_worker": "recovery_worker",
            "end": END,
        },
    )
    
    # Training workers → interrupt → on resume: finalize_workout then END (v1 logging)
    workflow.add_edge("iron_worker", "finalize_workout")
    workflow.add_edge("yoga_worker", "finalize_workout")
    workflow.add_edge("hiit_worker", "finalize_workout")
    workflow.add_edge("kb_worker", "finalize_workout")
    workflow.add_edge("finalize_workout", END)
    workflow.add_edge("recovery_worker", END)

    # Compile with breakpoint after training workers (user can log sets before finalize)
    if enable_persistence and SQLITE_AVAILABLE and SqliteSaver:
        Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
        db_path = Path(checkpoint_dir) / "checkpoints.db"
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        memory = SqliteSaver(conn)
        app = workflow.compile(
            checkpointer=memory,
            interrupt_after=["iron_worker", "yoga_worker", "hiit_worker", "kb_worker"],
        )
    else:
        app = workflow.compile()

    return app


def run_workout(
    user_id: str,
    persona: Literal["iron", "yoga", "hiit", "kickboxing"],
    goal: str,
    fatigue_scores: dict,
    messages: list[dict] | None = None,
    checkpoint_dir: str = "checkpoints",
) -> dict:
    """
    Run the complete workout generation workflow.
    
    Args:
        user_id: User identifier
        persona: Selected training persona
        goal: User's fitness goal
        fatigue_scores: Current fatigue scores
        messages: Conversation history (optional)
        checkpoint_dir: Directory for state persistence
    
    Returns:
        Final state with generated workout
    """
    import time
    
    # Build initial state with safety defaults
    initial_state: FitnessState = {
        "user_id": user_id,
        "selected_persona": persona,
        "selected_creator": persona,  # Legacy compatibility
        "next_node": "",
        "fatigue_scores": fatigue_scores,
        "last_session_timestamp": time.time(),
        "workout_history": [],  # Will be loaded from persistence if available
        "max_workouts_per_week": 4,  # Default: 4 workouts per week
        "workouts_completed_this_week": 0,  # Will be loaded from persistence
        "fatigue_threshold": 0.8,  # Default: 0.8 (80% fatigue triggers recovery)
        "messages": messages or [],
        "active_philosophy": None,
        "retrieved_rules": [],
        "retrieved_philosophy": "",
        "goal": goal,
        "current_workout": None,
        "daily_workout": None,
        "is_approved": False,
        "active_logs": [],
        "is_working_out": False,
    }
    
    # Build and run graph with persistence enabled
    app = build_graph(checkpoint_dir, enable_persistence=True)
    
    # Run with thread_id for persistence
    # Each user_id maps to a unique thread_id, allowing per-user state isolation
    config = {"configurable": {"thread_id": user_id}}
    
    # Try to load existing state using db_utils (safer than get_state)
    # This avoids triggering LangGraph's checkpoint loading which might be corrupted
    try:
        if SQLITE_AVAILABLE and SqliteSaver:
            from db_utils import get_user_state
            existing_state = get_user_state(user_id, checkpoint_dir)
            if existing_state:
                # Preserve workout_history from persisted state
                if existing_state.get("workout_history"):
                    initial_state["workout_history"] = existing_state["workout_history"]
                # Merge fatigue_scores: keep persisted ones, update with provided ones
                if existing_state.get("fatigue_scores"):
                    merged_fatigue = {**existing_state["fatigue_scores"], **fatigue_scores}
                    initial_state["fatigue_scores"] = merged_fatigue
                # Preserve safety settings from persisted state
                if existing_state.get("max_workouts_per_week"):
                    initial_state["max_workouts_per_week"] = existing_state["max_workouts_per_week"]
                if existing_state.get("workouts_completed_this_week") is not None:
                    initial_state["workouts_completed_this_week"] = existing_state["workouts_completed_this_week"]
                if existing_state.get("fatigue_threshold"):
                    initial_state["fatigue_threshold"] = existing_state["fatigue_threshold"]
                if "active_logs" in existing_state:
                    initial_state["active_logs"] = existing_state.get("active_logs") or []
                if "is_working_out" in existing_state:
                    initial_state["is_working_out"] = existing_state.get("is_working_out", False)
                # IMPORTANT: Always override selected_persona with the new persona parameter
                # This ensures persona changes are respected
                initial_state["selected_persona"] = persona
                initial_state["selected_creator"] = persona  # Legacy compatibility
                # IMPORTANT: Clear daily_workout when starting a new workout request
                # This ensures we don't keep the old workout when generating a new one
                initial_state["daily_workout"] = None
                initial_state["current_workout"] = None
                initial_state["is_working_out"] = False
    except Exception:
        # If loading fails, continue with provided initial_state
        pass
    
    # Invoke the graph
    # If checkpoint is corrupted, LangGraph will error - we'll handle it below
    try:
        result = app.invoke(initial_state, config)
    except KeyError as e:
        if "step" in str(e):
            # Corrupted checkpoint - delete and retry with fresh state (no merged fatigue)
            print(f"⚠️  Corrupted checkpoint detected. Deleting and retrying...")
            try:
                from db_utils import delete_user
                delete_user(user_id, checkpoint_dir)
                # Retry with fresh initial_state (no merge) so we don't pass stale high fatigue
                fresh_state: FitnessState = {
                    "user_id": user_id,
                    "selected_persona": persona,
                    "selected_creator": persona,
                    "next_node": "",
                    "fatigue_scores": fatigue_scores,
                    "last_session_timestamp": time.time(),
                    "workout_history": [],
                    "max_workouts_per_week": 4,
                    "workouts_completed_this_week": 0,
                    "fatigue_threshold": 0.8,
                    "messages": messages or [],
                    "active_philosophy": None,
                    "retrieved_rules": [],
                    "retrieved_philosophy": "",
                    "goal": goal,
                    "current_workout": None,
                    "daily_workout": None,
                    "is_approved": False,
                    "active_logs": [],
                    "is_working_out": False,
                }
                result = app.invoke(fresh_state, config)
            except Exception as retry_error:
                raise Exception(f"Failed to recover from corrupted checkpoint: {retry_error}") from e
        else:
            raise
    
    return result


def log_rest_day(
    user_id: str,
    checkpoint_dir: str = "checkpoints",
) -> dict:
    """
    Log a rest day and apply fatigue reduction through the graph system.
    
    This function uses the graph's checkpoint system to properly update state
    with rest day fatigue reduction.
    
    Args:
        user_id: User identifier
        checkpoint_dir: Directory for state persistence
    
    Returns:
        Updated state with reduced fatigue scores
    """
    # Build graph with persistence
    app = build_graph(checkpoint_dir, enable_persistence=True)
    config = {"configurable": {"thread_id": user_id}}
    
    # Get current state
    try:
        state_snapshot = app.get_state(config)
        if state_snapshot:
            values = getattr(state_snapshot, "values", state_snapshot)
            if isinstance(values, dict):
                current_state = values
            else:
                current_state = getattr(values, "__dict__", {}) or {}
        else:
            # No existing state, create minimal state
            import time
            current_state = {
                "user_id": user_id,
                "fatigue_scores": {},
                "last_session_timestamp": time.time(),
            }
    except Exception:
        # If getting state fails, create minimal state
        import time
        current_state = {
            "user_id": user_id,
            "fatigue_scores": {},
            "last_session_timestamp": time.time(),
        }
    
    # Apply rest day fatigue reduction
    rest_result = log_rest_node(current_state)
    
    # Update state via graph checkpoint system
    app.update_state(
        config,
        {
            "fatigue_scores": rest_result.get("fatigue_scores", {}),
            "last_session_timestamp": rest_result.get("last_session_timestamp"),
        }
    )
    
    # Return updated state
    state_snapshot = app.get_state(config)
    if state_snapshot:
        values = getattr(state_snapshot, "values", state_snapshot)
        if isinstance(values, dict):
            return values
        return getattr(values, "__dict__", {}) or {}
    return current_state


if __name__ == "__main__":
    # Example usage
    result = run_workout(
        user_id="test_user",
        persona="iron",
        goal="Build strength",
        fatigue_scores={"legs": 0.3, "push": 0.2, "pull": 0.1},
        messages=[{"role": "user", "content": "I want a strength workout today"}],
    )
    
    print("Generated Workout:")
    print(result.get("daily_workout"))
