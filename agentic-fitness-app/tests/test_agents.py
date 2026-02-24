"""
Test individual agents in isolation.

Each test calls the agent function directly with a crafted FitnessState,
bypassing the full LangGraph flow.

Usage:
    # Run all agent tests
    pytest tests/test_agents.py -v -s

    # Run a single agent test
    pytest tests/test_agents.py::test_supervisor_frequency_block -v -s
    pytest tests/test_agents.py::test_supervisor_fatigue_override -v -s
    pytest tests/test_agents.py::test_supervisor_routes_to_qa -v -s
    pytest tests/test_agents.py::test_supervisor_llm_routing -v -s
    pytest tests/test_agents.py::test_recommender -v -s
    pytest tests/test_agents.py::test_qa_agent -v -s
    pytest tests/test_agents.py::test_greeting -v -s
    pytest tests/test_agents.py::test_recovery_worker -v -s
    pytest tests/test_agents.py::test_finalize_workout -v -s

    # Run as script
    python -m tests.test_agents
"""

import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config  # noqa: F401 — load .env


def _base_state(**overrides) -> dict:
    """Minimal FitnessState with sensible defaults. Override any field via kwargs."""
    state = {
        "user_id": f"test_agent_{int(time.time() * 1000)}",
        "selected_persona": "iron",
        "selected_creator": "coach_iron",
        "next_node": "",
        "height_cm": 175.0,
        "weight_kg": 75.0,
        "fitness_level": "Intermediate",
        "about_me": "Software engineer, likes hiking",
        "is_onboarded": True,
        "recommended_personas": None,
        "recommended_persona": None,
        "recommendation_rationale": None,
        "subscribed_personas": ["iron", "yoga"],
        "fatigue_scores": {"legs": 0.3, "push": 0.2, "pull": 0.1},
        "last_session_timestamp": time.time() - 86400,
        "workout_history": [],
        "max_workouts_per_week": 4,
        "workouts_completed_this_week": 1,
        "fatigue_threshold": 0.8,
        "messages": [],
        "performance_tone": None,
        "tonality_hint": None,
        "active_philosophy": None,
        "retrieved_rules": [],
        "retrieved_philosophy": "",
        "goal": "Build strength and stay flexible",
        "current_workout": None,
        "daily_workout": None,
        "is_approved": False,
        "active_logs": None,
        "is_working_out": None,
        "recommendation_pending": None,
        "chat_response": None,
        "equipment": None,
        "workout_duration_minutes": None,
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# Supervisor tests (mix of deterministic short-circuits and LLM routing)
# ---------------------------------------------------------------------------

def test_supervisor_frequency_block():
    """Supervisor blocks when weekly limit is reached (no LLM call)."""
    from agents.supervisor import supervisor_node

    state = _base_state(
        workouts_completed_this_week=4,
        max_workouts_per_week=4,
        messages=[{"role": "user", "content": "Give me a leg day"}],
    )
    result = supervisor_node(state)
    print(f"\n[Frequency Block] next_node={result['next_node']}")
    assert result["next_node"] == "end", f"Expected 'end', got {result['next_node']}"


def test_supervisor_fatigue_override():
    """Supervisor forces recovery when fatigue exceeds threshold (no LLM call)."""
    from agents.supervisor import supervisor_node

    state = _base_state(
        fatigue_scores={"legs": 0.95, "push": 0.4, "pull": 0.2},
        messages=[{"role": "user", "content": "I want a heavy squat day"}],
    )
    result = supervisor_node(state)
    print(f"\n[Fatigue Override] next_node={result['next_node']}")
    assert result["next_node"] == "recovery_worker", f"Expected 'recovery_worker', got {result['next_node']}"


def test_supervisor_routes_to_qa():
    """Supervisor routes questions to qa_worker (no LLM call)."""
    from agents.supervisor import supervisor_node

    state = _base_state(
        messages=[{"role": "user", "content": "How many workouts do I have left this week?"}],
    )
    result = supervisor_node(state)
    print(f"\n[QA Route] next_node={result['next_node']}")
    assert result["next_node"] == "qa_worker", f"Expected 'qa_worker', got {result['next_node']}"


def test_supervisor_direct_route():
    """Supervisor routes directly to current persona worker when no complaints (no LLM call)."""
    from agents.supervisor import supervisor_node

    state = _base_state(
        messages=[{"role": "user", "content": "Give me a workout"}],
    )
    result = supervisor_node(state)
    print(f"\n[Direct Route] next_node={result['next_node']}, persona={result['selected_persona']}")
    assert result["next_node"] in ("iron_worker", "yoga_worker", "hiit_worker", "kb_worker")


def test_supervisor_llm_routing():
    """Supervisor uses LLM when user has complaints/persona-switch keywords (REQUIRES LLM)."""
    from agents.supervisor import supervisor_node

    state = _base_state(
        fatigue_scores={"legs": 0.3, "push": 0.2, "pull": 0.1},
        messages=[{"role": "user", "content": "My legs are sore, maybe I should do yoga today"}],
    )
    result = supervisor_node(state)
    print(f"\n[LLM Routing] next_node={result['next_node']}, persona={result['selected_persona']}")
    print(f"  Updated fatigue: {result.get('fatigue_scores', {})}")
    assert result["next_node"] in (
        "iron_worker", "yoga_worker", "hiit_worker", "kb_worker",
        "recovery_worker", "qa_worker", "end",
    )


# ---------------------------------------------------------------------------
# Recommender (REQUIRES LLM)
# ---------------------------------------------------------------------------

def test_recommender():
    """Recommender suggests personas but does NOT auto-onboard (recommendation_pending=True)."""
    from agents.recommender import persona_recommendation_node

    state = _base_state(
        is_onboarded=False,
        goal="Lose weight and improve flexibility",
        fitness_level="Beginner",
        about_me="Office worker, sedentary lifestyle, wants to get healthier",
    )
    result = persona_recommendation_node(state)
    print(f"\n[Recommender] recommended_personas={result.get('recommended_personas')}")
    print(f"  subscribed_personas={result.get('subscribed_personas')}")
    print(f"  rationale={result.get('recommendation_rationale')}")
    assert result.get("recommended_personas"), "Expected at least one recommended persona"
    assert result.get("recommendation_pending") is True, "Expected recommendation_pending=True"
    assert "is_onboarded" not in result, "Recommender should no longer set is_onboarded"


def test_recommender_refine():
    """Refine adapts recommendation based on user feedback (REQUIRES LLM)."""
    from agents.recommender import persona_recommendation_node, refine_recommendation

    # First get an initial recommendation
    state = _base_state(
        is_onboarded=False,
        goal="Lose weight",
        fitness_level="Beginner",
        about_me="Office worker",
    )
    initial = persona_recommendation_node(state)
    print(f"\n[Refine] Initial recommendation: {initial.get('recommended_personas')}")

    # Now refine with feedback
    state_with_rec = {**state, **initial}
    refined = refine_recommendation(state_with_rec, "I also want HIIT for cardio")
    print(f"  Refined recommendation: {refined.get('recommended_personas')}")
    print(f"  Refined rationale: {refined.get('recommendation_rationale')}")
    assert refined.get("recommended_personas"), "Expected at least one recommended persona"
    assert refined.get("recommendation_pending") is True


# ---------------------------------------------------------------------------
# QA Agent (REQUIRES LLM)
# ---------------------------------------------------------------------------

def test_qa_agent():
    """QA agent answers a fitness question using user state context."""
    from agents.qa_agent import qa_worker_node

    state = _base_state(
        fatigue_scores={"legs": 0.6, "push": 0.3, "pull": 0.1},
        workouts_completed_this_week=2,
        messages=[{"role": "user", "content": "Why is my leg fatigue so high?"}],
    )
    result = qa_worker_node(state)
    answer = result.get("chat_response", "")
    print(f"\n[QA Agent] answer={answer}")
    assert answer, "Expected a non-empty answer"
    assert result.get("daily_workout") is None, "QA should not produce a workout"


def test_qa_standalone():
    """QA standalone helper (used by WebSocket CHAT_MESSAGE handler)."""
    from agents.qa_agent import run_qa_standalone

    user_state = _base_state(
        fatigue_scores={"legs": 0.7, "push": 0.5},
        workouts_completed_this_week=3,
    )
    answer = run_qa_standalone(user_state, "How many workouts do I have left?")
    print(f"\n[QA Standalone] answer={answer}")
    assert answer, "Expected a non-empty answer"


# ---------------------------------------------------------------------------
# Greeting (REQUIRES LLM if ENABLE_GREETING_LLM=True, otherwise template)
# ---------------------------------------------------------------------------

def test_greeting():
    """Greeting agent generates a personalized greeting."""
    from agents.greeting import generate_greeting

    greeting = generate_greeting(
        user_id="aashish_test",
        about_me="Software engineer at AWS, likes hiking in Zion, sensitive knees",
        workout_history=[
            {"_active_logs": [{"sets": [{"rpe": 8}, {"rpe": 9}]}]},
        ],
    )
    print(f"\n[Greeting] greeting={greeting}")
    assert greeting, "Expected a non-empty greeting"


# ---------------------------------------------------------------------------
# Recovery Worker (REQUIRES LLM)
# ---------------------------------------------------------------------------

def test_recovery_worker():
    """Recovery worker generates a recovery plan for high fatigue."""
    from agents.recovery_worker import recovery_worker

    state = _base_state(
        fatigue_scores={"legs": 0.9, "push": 0.85, "pull": 0.7},
        goal="Recover and return stronger",
    )
    result = recovery_worker(state)
    plan = result.get("daily_workout", {})
    print(f"\n[Recovery Worker] recovery_focus={plan.get('recovery_focus')}")
    print(f"  activities={len(plan.get('activities', []))}")
    print(f"  permission_to_rest={plan.get('permission_to_rest', '')[:80]}...")
    assert plan.get("activities"), "Expected recovery activities"
    assert plan.get("permission_to_rest"), "Expected permission_to_rest message"


# ---------------------------------------------------------------------------
# Finalize Workout (deterministic, no LLM)
# ---------------------------------------------------------------------------

def test_finalize_workout():
    """Finalize appends workout to history, increments counter, applies fatigue."""
    from agents.finalize_workout import finalize_workout_node

    state = _base_state(
        daily_workout={
            "focus_area": "Legs",
            "exercises": [{"exercise_name": "Squat", "sets": 3, "reps": 5}],
        },
        active_logs=[
            {"muscle_group": "legs", "sets": [{"rpe": 8}, {"rpe": 9}]},
        ],
        workouts_completed_this_week=1,
        fatigue_scores={"legs": 0.3, "push": 0.2},
    )
    result = finalize_workout_node(state)
    print(f"\n[Finalize] workouts_completed={result['workouts_completed_this_week']}")
    print(f"  fatigue_scores={result['fatigue_scores']}")
    print(f"  history_len={len(result['workout_history'])}")
    assert result["workouts_completed_this_week"] == 2
    assert result["fatigue_scores"]["legs"] > 0.3, "Legs fatigue should increase"
    assert result["daily_workout"] is None, "daily_workout should be cleared"
    assert len(result["workout_history"]) >= 1


def test_finalize_workout_no_logs():
    """Finalize applies default fatigue when no logs were recorded."""
    from agents.finalize_workout import finalize_workout_node

    state = _base_state(
        daily_workout={
            "focus_area": "Push (Chest & Shoulders)",
            "exercises": [{"exercise_name": "Bench Press", "sets": 4, "reps": 8}],
        },
        active_logs=[],
        workouts_completed_this_week=0,
        fatigue_scores={"legs": 0.1, "push": 0.1},
    )
    result = finalize_workout_node(state)
    print(f"\n[Finalize No Logs] fatigue_scores={result['fatigue_scores']}")
    assert result["workouts_completed_this_week"] == 1
    assert result["fatigue_scores"]["push"] > 0.1, "Push fatigue should increase with default"


# ---------------------------------------------------------------------------
# Supervisor: Command detection (deterministic, no LLM)
# ---------------------------------------------------------------------------

def test_supervisor_routes_commands_to_qa():
    """Supervisor routes command-like messages to qa_worker."""
    from agents.supervisor import supervisor_node

    state = _base_state(
        messages=[{"role": "user", "content": "Reset my fatigue scores"}],
    )
    result = supervisor_node(state)
    print(f"\n[Supervisor Command] next_node={result['next_node']}")
    assert result["next_node"] == "qa_worker", "Commands should route to qa_worker"


def test_supervisor_context_aware_routing():
    """Supervisor picks yoga worker when message mentions flexibility (context-aware)."""
    from agents.supervisor import supervisor_node

    state = _base_state(
        subscribed_personas=["iron", "yoga"],
        messages=[{"role": "user", "content": "I want a flexibility session today"}],
    )
    result = supervisor_node(state)
    print(f"\n[Supervisor Context] next_node={result['next_node']}, persona={result['selected_persona']}")
    assert result["next_node"] == "yoga_worker", "Flexibility message should route to yoga_worker"
    assert result["selected_persona"] == "yoga"


def test_supervisor_command_equipment():
    """Supervisor routes equipment update to qa_worker."""
    from agents.supervisor import supervisor_node

    state = _base_state(
        messages=[{"role": "user", "content": "I just got a barbell and a bench press"}],
    )
    result = supervisor_node(state)
    print(f"\n[Supervisor Equipment Cmd] next_node={result['next_node']}")
    assert result["next_node"] == "qa_worker", "Equipment update should route to qa_worker"


def test_supervisor_command_duration():
    """Supervisor routes duration change to qa_worker."""
    from agents.supervisor import supervisor_node

    state = _base_state(
        messages=[{"role": "user", "content": "I only have 20 minutes today"}],
    )
    result = supervisor_node(state)
    print(f"\n[Supervisor Duration Cmd] next_node={result['next_node']}")
    assert result["next_node"] == "qa_worker", "Duration change should route to qa_worker"


# ---------------------------------------------------------------------------
# Run all tests as script
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        # Deterministic (no LLM needed)
        ("Supervisor: Frequency Block", test_supervisor_frequency_block),
        ("Supervisor: Fatigue Override", test_supervisor_fatigue_override),
        ("Supervisor: QA Route", test_supervisor_routes_to_qa),
        ("Supervisor: Direct Route", test_supervisor_direct_route),
        ("Finalize Workout", test_finalize_workout),
        ("Finalize Workout (No Logs)", test_finalize_workout_no_logs),
        ("Supervisor: Command → QA", test_supervisor_routes_commands_to_qa),
        ("Supervisor: Context-Aware Routing", test_supervisor_context_aware_routing),
        ("Supervisor: Equipment Cmd", test_supervisor_command_equipment),
        ("Supervisor: Duration Cmd", test_supervisor_command_duration),
        # LLM-dependent
        ("Supervisor: LLM Routing", test_supervisor_llm_routing),
        ("Recommender", test_recommender),
        ("Recommender: Refine", test_recommender_refine),
        ("QA Agent", test_qa_agent),
        ("QA Standalone", test_qa_standalone),
        ("Greeting", test_greeting),
        ("Recovery Worker", test_recovery_worker),
    ]

    print("=" * 70)
    print("Individual Agent Tests")
    print("=" * 70)
    passed, failed = 0, 0
    for name, fn in tests:
        print(f"\n{'─' * 50}")
        print(f"▶ {name}")
        try:
            fn()
            print(f"  ✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1

    print(f"\n{'=' * 70}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 70)
