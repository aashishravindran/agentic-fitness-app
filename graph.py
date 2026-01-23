"""
LangGraph Workflow for Hierarchical Multi-Agent Fitness System

Flow:
1. Supervisor Node (entry point - handles user interactions, routing decision)
2. Decay Node (fatigue decay based on time - runs automatically)
3. Worker Node (specialized workout generation)
4. End

The Supervisor is the primary entry point for all user interactions.
"""

from __future__ import annotations

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
from agents.supervisor import supervisor_node
from agents.workers import hiit_worker, iron_worker, kb_worker, yoga_worker
from state import FitnessState


def route_after_supervisor(state: FitnessState) -> Literal["iron_worker", "yoga_worker", "hiit_worker", "kb_worker", "end"]:
    """Route to the next node based on supervisor's decision."""
    next_node = state.get("next_node", "end")
    return next_node


def build_graph(checkpoint_dir: str = "checkpoints") -> StateGraph:
    """
    Build the LangGraph workflow.
    
    Args:
        checkpoint_dir: Directory for SqliteSaver persistence
    
    Returns:
        Compiled StateGraph ready to run
    """
    # Create graph
    workflow = StateGraph(FitnessState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)  # Entry point for user interactions
    workflow.add_node("decay", decay_node)  # Runs automatically after supervisor
    workflow.add_node("iron_worker", iron_worker)
    workflow.add_node("yoga_worker", yoga_worker)
    workflow.add_node("hiit_worker", hiit_worker)
    workflow.add_node("kb_worker", kb_worker)
    
    # Set entry point - Supervisor handles all user interactions
    workflow.set_entry_point("supervisor")
    
    # Flow: Supervisor (processes user) → Decay (updates fatigue) → Route to worker
    workflow.add_edge("supervisor", "decay")
    workflow.add_conditional_edges(
        "decay",
        route_after_supervisor,  # Route based on supervisor's next_node decision
        {
            "iron_worker": "iron_worker",
            "yoga_worker": "yoga_worker",
            "hiit_worker": "hiit_worker",
            "kb_worker": "kb_worker",
            "end": END,
        },
    )
    
    # All workers end
    workflow.add_edge("iron_worker", END)
    workflow.add_edge("yoga_worker", END)
    workflow.add_edge("hiit_worker", END)
    workflow.add_edge("kb_worker", END)
    
    # Compile graph
    # Note: SqliteSaver requires context manager usage, which is complex for long-lived apps
    # For now, we compile without persistence - the graph works fine without it
    # State persistence can be added later by managing SqliteSaver context at a higher level
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
    
    # Build initial state
    initial_state: FitnessState = {
        "user_id": user_id,
        "selected_persona": persona,
        "selected_creator": persona,  # Legacy compatibility
        "next_node": "",
        "fatigue_scores": fatigue_scores,
        "last_session_timestamp": time.time(),
        "messages": messages or [],
        "active_philosophy": None,
        "retrieved_rules": [],
        "retrieved_philosophy": "",
        "goal": goal,
        "current_workout": None,
        "daily_workout": None,
        "is_approved": False,
    }
    
    # Build and run graph
    app = build_graph(checkpoint_dir)
    
    # Run with thread_id for persistence
    config = {"configurable": {"thread_id": user_id}}
    result = app.invoke(initial_state, config)
    
    return result


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
