"""
How to Call the Supervisor Agent

You can use the Supervisor in two ways:

1. Call the Supervisor directly (supervisor_node) — routing + fatigue mapping only
2. Run the full workflow (run_workout) — Supervisor → Decay → Worker → workout
"""

import sys
import time
from pathlib import Path

# Ensure project root is on path (examples/ is one level down)
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config  # Load .env
from agents.supervisor import supervisor_node
from graph import run_workout
from state import FitnessState


# -----------------------------------------------------------------------------
# Option 1: Call the Supervisor directly
# -----------------------------------------------------------------------------
# Use this when you only want routing/fatigue decisions, not a full workout.

def call_supervisor_directly():
    """Call supervisor_node with a FitnessState. Returns routing + fatigue updates."""

    state: FitnessState = {
        "user_id": "user_123",
        "selected_persona": "iron",
        "selected_creator": "iron",
        "next_node": "",
        "fatigue_scores": {"legs": 0.3, "push": 0.2, "pull": 0.1},
        "last_session_timestamp": time.time(),
        "messages": [
            {"role": "user", "content": "I want to switch to yoga today, my hips are tight"},
        ],
        "active_philosophy": None,
        "retrieved_rules": [],
        "retrieved_philosophy": "",
        "goal": "Improve flexibility",
        "current_workout": None,
        "daily_workout": None,
        "is_approved": False,
    }

    # Call Supervisor directly
    updated = supervisor_node(state)

    print("Supervisor decision:")
    print(f"  next_node:      {updated['next_node']}")
    print(f"  selected_persona: {updated['selected_persona']}")
    print(f"  fatigue_scores: {updated['fatigue_scores']}")
    return updated


# -----------------------------------------------------------------------------
# Option 2: Run the full workflow (Supervisor is the entry point)
# -----------------------------------------------------------------------------
# Use this when you want a complete workout. Supervisor runs first, then decay, then worker.

def call_supervisor_via_workflow():
    """Run the full graph. Supervisor is the entry point; you get a workout at the end."""

    result = run_workout(
        user_id="user_123",
        persona="iron",
        goal="Build strength",
        fatigue_scores={"legs": 0.3, "push": 0.2, "pull": 0.1},
        messages=[
            {"role": "user", "content": "I want a strength workout today"},
        ],
    )

    print("Workout (from full workflow):")
    print(result.get("daily_workout"))
    return result


# -----------------------------------------------------------------------------
# Run examples
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Option 1: Call Supervisor directly (routing only)")
    print("=" * 60)
    call_supervisor_directly()

    print("\n" + "=" * 60)
    print("Option 2: Run full workflow (Supervisor → Decay → Worker)")
    print("=" * 60)
    call_supervisor_via_workflow()
