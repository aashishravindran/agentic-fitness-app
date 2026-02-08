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
from agents.recommender import persona_recommendation_node
from agents.supervisor import supervisor_node
from agents.workers import hiit_worker, iron_worker, kb_worker, yoga_worker
from feature_flags import ENABLE_DECAY, ENABLE_HISTORY_ANALYZER, ENABLE_PERSONA_RECOMMENDER
from state import FitnessState


def _passthrough_node(state: FitnessState) -> dict:
    """Identity node: passes state through for routing when decay/history are disabled."""
    return {}


def _after_supervisor(
    _state: FitnessState,
) -> Literal["decay", "history_analysis", "pre_route"]:
    """Route from supervisor: to decay, history_analysis, or pre_route based on feature flags."""
    if ENABLE_DECAY:
        return "decay"
    if ENABLE_HISTORY_ANALYZER:
        return "history_analysis"
    return "pre_route"


def _after_decay(
    _state: FitnessState,
) -> Literal["history_analysis", "pre_route"]:
    """Route from decay: to history_analysis or pre_route based on feature flags."""
    if ENABLE_HISTORY_ANALYZER:
        return "history_analysis"
    return "pre_route"


def _check_onboarding(state: FitnessState) -> Literal["recommender", "supervisor"]:
    """Conditional entry: route to recommender if not onboarded, else supervisor."""
    if not ENABLE_PERSONA_RECOMMENDER:
        return "supervisor"
    if state.get("is_onboarded", False):
        return "supervisor"
    return "recommender"


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

    # Routing target: identity node so we can attach conditional_edges
    workflow.add_node("pre_route", _passthrough_node)
    workflow.add_node("supervisor", supervisor_node)
    if ENABLE_PERSONA_RECOMMENDER:
        workflow.add_node("recommender", persona_recommendation_node)
    if ENABLE_DECAY:
        workflow.add_node("decay", decay_node)
    if ENABLE_HISTORY_ANALYZER:
        workflow.add_node("history_analysis", history_analysis_node)
    workflow.add_node("iron_worker", iron_worker)
    workflow.add_node("yoga_worker", yoga_worker)
    workflow.add_node("hiit_worker", hiit_worker)
    workflow.add_node("kb_worker", kb_worker)
    workflow.add_node("recovery_worker", recovery_worker)
    workflow.add_node("finalize_workout", finalize_workout_node)

    # Conditional entry: recommender for non-onboarded users, else supervisor
    if ENABLE_PERSONA_RECOMMENDER:
        workflow.set_conditional_entry_point(
            _check_onboarding,
            {"recommender": "recommender", "supervisor": "supervisor"},
        )
        workflow.add_edge("recommender", "supervisor")
    else:
        workflow.set_entry_point("supervisor")

    # Supervisor → decay | history_analysis | pre_route (based on feature flags)
    supervisor_targets: dict = {"pre_route": "pre_route"}
    if ENABLE_HISTORY_ANALYZER:
        supervisor_targets["history_analysis"] = "history_analysis"
    if ENABLE_DECAY:
        supervisor_targets["decay"] = "decay"
    workflow.add_conditional_edges("supervisor", _after_supervisor, supervisor_targets)

    if ENABLE_DECAY:
        decay_targets: dict = {"pre_route": "pre_route"}
        if ENABLE_HISTORY_ANALYZER:
            decay_targets["history_analysis"] = "history_analysis"
        workflow.add_conditional_edges("decay", _after_decay, decay_targets)

    if ENABLE_HISTORY_ANALYZER:
        workflow.add_edge("history_analysis", "pre_route")

    workflow.add_conditional_edges(
        "pre_route",
        route_after_supervisor,
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
            interrupt_after=["iron_worker", "yoga_worker", "hiit_worker", "kb_worker"],  # Pause after worker, before finalize (user can log sets)
        )
    else:
        app = workflow.compile()

    return app


def build_onboard_graph(checkpoint_dir: str = "checkpoints", enable_persistence: bool = True):
    """
    Build a minimal graph for onboarding: recommender only.
    Used by POST /users/{id}/onboard to run the persona recommender.
    """
    workflow = StateGraph(FitnessState)
    workflow.add_node("recommender", persona_recommendation_node)
    workflow.set_entry_point("recommender")
    workflow.add_edge("recommender", END)

    if enable_persistence and SQLITE_AVAILABLE and SqliteSaver:
        Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
        db_path = Path(checkpoint_dir) / "checkpoints.db"
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        memory = SqliteSaver(conn)
        return workflow.compile(checkpointer=memory)
    return workflow.compile()


def run_onboard(
    user_id: str,
    height_cm: float,
    weight_kg: float,
    goal: str,
    fitness_level: str = "Intermediate",
    checkpoint_dir: str = "checkpoints",
) -> dict:
    """
    Run the onboarding flow: recommender suggests a persona based on biometrics.

    Creates or updates state with biometric data, runs recommender, returns recommendation.
    """
    import time

    initial_state: FitnessState = {
        "user_id": user_id,
        "selected_persona": "iron",  # Default until recommender runs
        "selected_creator": "coach_iron",
        "next_node": "",
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "goal": goal,
        "fitness_level": fitness_level,
        "is_onboarded": False,
        "recommended_personas": None,
        "recommended_persona": None,
        "subscribed_personas": None,
        "fatigue_scores": {},
        "last_session_timestamp": time.time(),
        "workout_history": [],
        "max_workouts_per_week": 4,
        "workouts_completed_this_week": 0,
        "fatigue_threshold": 0.8,
        "messages": [],
        "active_philosophy": None,
        "retrieved_rules": [],
        "retrieved_philosophy": "",
        "current_workout": None,
        "daily_workout": None,
        "is_approved": False,
        "active_logs": [],
        "is_working_out": False,
    }

    app = build_onboard_graph(checkpoint_dir, enable_persistence=True)
    config = {"configurable": {"thread_id": user_id}}

    # Merge existing state if present (preserve fatigue, etc.)
    if SQLITE_AVAILABLE and SqliteSaver:
        from db_utils import get_user_state
        existing = get_user_state(user_id, checkpoint_dir)
        if existing:
            if existing.get("fatigue_scores"):
                initial_state["fatigue_scores"] = existing["fatigue_scores"]
            if existing.get("max_workouts_per_week"):
                initial_state["max_workouts_per_week"] = existing["max_workouts_per_week"]
            if existing.get("workouts_completed_this_week") is not None:
                initial_state["workouts_completed_this_week"] = existing["workouts_completed_this_week"]
            if existing.get("fatigue_threshold"):
                initial_state["fatigue_threshold"] = existing["fatigue_threshold"]

    try:
        result = app.invoke(initial_state, config)
        return result
    except KeyError as e:
        # Corrupted/incompatible checkpoint (e.g. missing 'pending_sends' from older LangGraph)
        err = str(e).lower()
        if "pending_sends" in err or "step" in err or "checkpoint" in err:
            from db_utils import delete_user
            delete_user(user_id, checkpoint_dir)
            result = app.invoke(initial_state, config)
            return result
        raise


def run_workout(
    user_id: str,
    persona: Literal["iron", "yoga", "hiit", "kickboxing"],
    goal: str,
    fatigue_scores: dict,
    messages: list[dict] | None = None,
    checkpoint_dir: str = "checkpoints",
    max_workouts_per_week: int | None = None,
    subscribed_personas: list[str] | None = None,
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
    
    # Build initial state with safety defaults.
    # is_onboarded=True when persona is explicitly provided (skip recommender for CLI/API).
    initial_state: FitnessState = {
        "user_id": user_id,
        "selected_persona": persona,
        "selected_creator": persona,  # Legacy compatibility
        "next_node": "",
        "is_onboarded": True,
        "fatigue_scores": fatigue_scores,
        "last_session_timestamp": time.time(),
        "workout_history": [],  # Will be loaded from persistence if available
        "max_workouts_per_week": max_workouts_per_week if max_workouts_per_week is not None else 4,  # Default: 4 workouts per week
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
    if subscribed_personas is not None:
        initial_state["subscribed_personas"] = subscribed_personas

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
                if "is_onboarded" in existing_state:
                    initial_state["is_onboarded"] = existing_state["is_onboarded"]
                if "recommended_persona" in existing_state:
                    initial_state["recommended_persona"] = existing_state["recommended_persona"]
                if "recommended_personas" in existing_state:
                    initial_state["recommended_personas"] = existing_state["recommended_personas"]
                if "subscribed_personas" in existing_state:
                    initial_state["subscribed_personas"] = existing_state["subscribed_personas"]
                if "height_cm" in existing_state:
                    initial_state["height_cm"] = existing_state.get("height_cm")
                if "weight_kg" in existing_state:
                    initial_state["weight_kg"] = existing_state.get("weight_kg")
                if "fitness_level" in existing_state:
                    initial_state["fitness_level"] = existing_state.get("fitness_level")
    except Exception:
        # If loading fails, continue with provided initial_state
        pass
    
    # Invoke the graph
    # If checkpoint is corrupted, LangGraph will error - we'll handle it below
    try:
        result = app.invoke(initial_state, config)
    except KeyError as e:
        # Incompatible/corrupted checkpoint (e.g. missing 'pending_sends' from older LangGraph) - delete and retry
        err = str(e).lower()
        if "step" in err or "pending_sends" in err or "checkpoint" in err:
            print(f"⚠️  Corrupted checkpoint detected ({e}). Deleting and retrying...")
            try:
                from db_utils import delete_user
                delete_user(user_id, checkpoint_dir)
                # Retry with fresh initial_state (no merge) so we don't pass stale high fatigue
                fresh_state: FitnessState = {
                    "user_id": user_id,
                    "selected_persona": persona,
                    "selected_creator": persona,
                    "next_node": "",
                    "is_onboarded": True,
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
