"""
End-to-end tests for the workout flow.

Covers:
- Exercise IDs: exercises have id (ex_0, ex_1, ...) for reliable log-set matching
- Interrupt after worker: graph pauses after worker, before finalize (user can log sets)
- Log-set by exercise_id and by exercise name
- Finish-workout: resumes graph, runs finalize, clears daily_workout, saves to history

Run from project root (requires: pip install -r requirements.txt, ingest, LLM configured):
  python -m pytest tests/test_e2e_workout_flow.py -v
  python -m pytest tests/test_e2e_workout_flow.py -v -s  # show print output
  python tests/test_e2e_workout_flow.py  # run as script
"""

import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config  # Load .env

# Pytest or plain Python
try:
    import pytest
except ImportError:
    pytest = None


def _unique_user() -> str:
    return f"e2e_{int(time.time() * 1000)}"


def _ensure_onboarded(client, user_id: str):
    """Onboard user and select persona. Creates user in checkpoint DB."""
    onboard_resp = client.post(
        f"/api/users/{user_id}/onboard",
        json={
            "height_cm": 175,
            "weight_kg": 75,
            "goal": "Build strength",
            "fitness_level": "Intermediate",
        },
    )
    if onboard_resp.status_code == 409:
        return  # Already onboarded
    assert onboard_resp.status_code == 200, f"Onboard failed: {onboard_resp.text}"

    # Select iron persona for strength workout
    select_resp = client.post(
        f"/api/users/{user_id}/select-persona",
        json={"personas": ["iron"]},
    )
    assert select_resp.status_code == 200, f"Select persona failed: {select_resp.text}"


def test_workout_flow_exercise_ids_interrupt_log_finish():
    """
    Full e2e: onboard -> generate workout -> verify exercise IDs -> log by id -> log by name -> finish.
    """
    from fastapi.testclient import TestClient

    from backend.main import app
    from db_utils import delete_user, get_user_state

    client = TestClient(app)
    user_id = _unique_user()

    try:
        _ensure_onboarded(client, user_id)

        # 1. Generate workout (graph runs until worker, then interrupts)
        gen_resp = client.post(
            f"/api/users/{user_id}/workout",
            json={"prompt": "I want a short leg workout with 2 exercises"},
        )
        assert gen_resp.status_code == 200, f"Generate failed: {gen_resp.text}"
        data = gen_resp.json()
        workout = data.get("workout")
        state = data.get("state", {})

        assert workout, "Expected workout in response"
        assert state.get("is_working_out") is True, "Expected is_working_out=True after interrupt"

        exercises = workout.get("exercises") or workout.get("poses") or workout.get("activities")
        assert exercises, "Expected exercises/poses/activities in workout"
        assert len(exercises) >= 1, "Need at least one exercise"

        # 2. Verify exercise IDs exist
        for i, ex in enumerate(exercises):
            assert "id" in ex, f"Exercise {i} missing id: {ex}"
            assert ex["id"] == f"ex_{i}", f"Expected id ex_{i}, got {ex['id']}"

        first_ex = exercises[0]
        first_id = first_ex["id"]
        first_name = first_ex.get("exercise_name") or first_ex.get("pose_name") or first_ex.get("activity_name")

        # 3. Log set by exercise_id
        log_resp = client.post(
            f"/api/users/{user_id}/log-set",
            json={"exercise_id": first_id, "weight": 100, "reps": 5, "rpe": 8},
        )
        assert log_resp.status_code == 200, f"Log set by id failed: {log_resp.text}"
        log_state = log_resp.json().get("state", {})
        active_logs = log_state.get("active_logs", [])
        assert any(e.get("exercise_id") == first_id or e.get("exercise_name") == first_name for e in active_logs)

        # 4. Log set by exercise name (second exercise if exists)
        if len(exercises) >= 2:
            second_ex = exercises[1]
            second_name = second_ex.get("exercise_name") or second_ex.get("pose_name") or second_ex.get("activity_name")
            log2_resp = client.post(
                f"/api/users/{user_id}/log-set",
                json={"exercise": second_name, "weight": 80, "reps": 8, "rpe": 6},
            )
            assert log2_resp.status_code == 200, f"Log set by name failed: {log2_resp.text}"

        # 5. Finish workout (resumes graph, runs finalize)
        finish_resp = client.post(f"/api/users/{user_id}/finish-workout")
        assert finish_resp.status_code == 200, f"Finish workout failed: {finish_resp.text}"
        finish_data = finish_resp.json()
        assert finish_data.get("workout_completed") is True

        # 6. Verify state: daily_workout cleared, workout in history
        persisted = get_user_state(user_id)
        assert persisted is not None
        assert persisted.get("daily_workout") is None, "daily_workout should be cleared after finalize"
        history = persisted.get("workout_history", [])
        assert len(history) >= 1, "Workout should be in history"
        last_workout = history[-1]
        assert last_workout.get("exercises") or last_workout.get("poses") or last_workout.get("activities")

    finally:
        delete_user(user_id)


def test_log_set_requires_exercise_or_id():
    """Log-set returns 400 when neither exercise nor exercise_id provided."""
    from fastapi.testclient import TestClient

    from backend.main import app
    from db_utils import delete_user

    client = TestClient(app)
    user_id = _unique_user()

    try:
        _ensure_onboarded(client, user_id)
        gen_resp = client.post(
            f"/api/users/{user_id}/workout",
            json={"prompt": "Short leg workout"},
        )
        assert gen_resp.status_code == 200

        bad_resp = client.post(
            f"/api/users/{user_id}/log-set",
            json={"weight": 100, "reps": 5, "rpe": 8},
        )
        assert bad_resp.status_code == 400
        assert "exercise" in bad_resp.json().get("detail", "").lower() or "exercise_id" in bad_resp.json().get("detail", "").lower()
    finally:
        delete_user(user_id)


def test_log_set_invalid_exercise_id():
    """Log-set returns 400 when exercise_id not found in workout."""
    from fastapi.testclient import TestClient

    from backend.main import app
    from db_utils import delete_user

    client = TestClient(app)
    user_id = _unique_user()

    try:
        _ensure_onboarded(client, user_id)
        gen_resp = client.post(
            f"/api/users/{user_id}/workout",
            json={"prompt": "Short leg workout"},
        )
        assert gen_resp.status_code == 200

        bad_resp = client.post(
            f"/api/users/{user_id}/log-set",
            json={"exercise_id": "ex_99", "weight": 100, "reps": 5, "rpe": 8},
        )
        assert bad_resp.status_code == 400
    finally:
        delete_user(user_id)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("E2E Workout Flow Tests")
    print("=" * 70)
    print("Requires: LLM (Gemini/Ollama), ingest, ENABLE_PERSONA_RECOMMENDER=True")
    print("=" * 70 + "\n")

    if pytest:
        sys.exit(pytest.main([__file__, "-v", "-s"]))
    else:
        # Run without pytest
        test_workout_flow_exercise_ids_interrupt_log_finish()
        test_log_set_requires_exercise_or_id()
        test_log_set_invalid_exercise_id()
        print("\n✅ All E2E tests passed")
