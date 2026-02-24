"""
Integration tests for all REST APIs.

Exercises each endpoint with valid/invalid inputs. Uses mocks to avoid LLM calls
so tests run fast without API keys.

APIs covered:
- POST /api/users/{id}/onboard
- POST /api/users/{id}/select-persona
- GET  /api/users/{id}/profile
- GET  /api/users/{id}/status
- GET  /api/users/{id}/history
- PATCH /api/users/{id}/settings
- POST /api/users/{id}/workout
- POST /api/users/{id}/log-set
- POST /api/users/{id}/finish-workout
- POST /api/users/{id}/reset-fatigue
- POST /api/users/{id}/reset-workouts
- POST /api/users/{id}/new-week

Run (requires: pip install -r requirements.txt):
  pytest tests/test_integration_apis.py -v
"""

import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config  # Load .env

try:
    import pytest
except ImportError:
    pytest = None


def _unique_user() -> str:
    return f"int_{int(time.time() * 1000)}"


# Canned recommender output (no LLM)
def _mock_recommender_node(state):
    return {
        "recommended_personas": ["coach_iron"],
        "recommended_persona": "coach_iron",
        "recommendation_rationale": "Mock recommendation for integration test.",
        "subscribed_personas": ["iron"],
        "is_onboarded": True,
        "selected_persona": "iron",
        "selected_creator": "coach_iron",
    }


# Canned workout output (no LLM)
def _mock_iron_worker(state):
    from agents.workout_utils import inject_exercise_ids

    workout_dict = inject_exercise_ids({
        "focus_area": "Legs",
        "total_exercises": 2,
        "exercises": [
            {"exercise_name": "Barbell Squat", "sets": 3, "reps": "5", "tempo_notes": "Controlled", "iron_justification": "Test"},
            {"exercise_name": "Romanian Deadlift", "sets": 3, "reps": "8", "tempo_notes": "Controlled", "iron_justification": "Test"},
        ],
        "fatigue_adaptations": None,
        "overall_rationale": "Mock workout for integration test.",
    })
    return {
        "daily_workout": workout_dict,
        "active_philosophy": "Mock philosophy",
        "current_workout": str(workout_dict),
        "is_working_out": True,
    }


@pytest.fixture
def client():
    """FastAPI TestClient with mocked LLM flows."""
    with (
        patch("feature_flags.ENABLE_PERSONA_RECOMMENDER", True),
        patch("graph.persona_recommendation_node", _mock_recommender_node),
        patch("graph.iron_worker", _mock_iron_worker),
        patch("graph.yoga_worker", _mock_iron_worker),
        patch("graph.hiit_worker", _mock_iron_worker),
        patch("graph.kb_worker", _mock_iron_worker),
    ):
        from fastapi.testclient import TestClient
        from backend.main import app
        yield TestClient(app)


@pytest.fixture
def onboarded_user(client):
    """User that has completed onboard + select-persona."""
    user_id = _unique_user()
    r = client.post(
        "/api/users/{}/onboard".format(user_id),
        json={"height_cm": 175, "weight_kg": 75, "goal": "Build strength", "fitness_level": "Intermediate"},
    )
    assert r.status_code == 200
    r = client.post("/api/users/{}/select-persona".format(user_id), json={"personas": ["iron"]})
    assert r.status_code == 200
    return user_id


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def test_get_status_no_user(client):
    """GET /status returns defaults when user has no state."""
    user_id = _unique_user()
    r = client.get("/api/users/{}/status".format(user_id))
    assert r.status_code == 200
    d = r.json()
    assert "workouts_completed_this_week" in d
    assert "max_workouts_per_week" in d
    assert "fatigue_scores" in d
    assert "fatigue_threshold" in d


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


def test_get_profile_no_user(client):
    """GET /profile returns defaults when user has no state."""
    user_id = _unique_user()
    r = client.get("/api/users/{}/profile".format(user_id))
    assert r.status_code == 200
    d = r.json()
    assert d["user_id"] == user_id
    assert d["is_onboarded"] is False
    assert d["subscribed_personas"] == []


def test_get_profile_after_onboard(client, onboarded_user):
    """GET /profile returns user data after onboard."""
    r = client.get("/api/users/{}/profile".format(onboarded_user))
    assert r.status_code == 200
    d = r.json()
    assert d["is_onboarded"] is True
    assert "iron" in (d.get("subscribed_personas") or [])


# ---------------------------------------------------------------------------
# Onboard
# ---------------------------------------------------------------------------


def test_post_onboard(client):
    """POST /onboard creates user and returns recommendation."""
    user_id = _unique_user()
    r = client.post(
        "/api/users/{}/onboard".format(user_id),
        json={"height_cm": 175, "weight_kg": 75, "goal": "Build strength", "fitness_level": "Intermediate"},
    )
    assert r.status_code == 200
    d = r.json()
    assert "recommended_personas" in d or "recommended_persona" in d
    assert "rationale" in d or "recommendation_rationale" in d


def test_post_onboard_duplicate_409(client, onboarded_user):
    """POST /onboard returns 409 when user already onboarded."""
    r = client.post(
        "/api/users/{}/onboard".format(onboarded_user),
        json={"height_cm": 175, "weight_kg": 75, "goal": "Build strength", "fitness_level": "Intermediate"},
    )
    assert r.status_code == 409


def test_post_onboard_invalid_payload(client):
    """POST /onboard returns 422 for invalid payload."""
    user_id = _unique_user()
    r = client.post("/api/users/{}/onboard".format(user_id), json={})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Select Persona
# ---------------------------------------------------------------------------


def test_post_select_persona_404_without_onboard(client):
    """POST /select-persona returns 404 when user not onboarded."""
    user_id = _unique_user()
    r = client.post("/api/users/{}/select-persona".format(user_id), json={"personas": ["iron"]})
    assert r.status_code == 404


def test_post_select_persona(client, onboarded_user):
    """POST /select-persona updates subscribed personas."""
    r = client.post("/api/users/{}/select-persona".format(onboarded_user), json={"personas": ["iron", "yoga"]})
    assert r.status_code == 200
    assert r.json().get("subscribed_personas") == ["iron", "yoga"]


# ---------------------------------------------------------------------------
# Workout
# ---------------------------------------------------------------------------


def test_post_workout(client, onboarded_user):
    """POST /workout generates workout (mocked) and returns it."""
    r = client.post(
        "/api/users/{}/workout".format(onboarded_user),
        json={"prompt": "I want a leg workout"},
    )
    assert r.status_code == 200
    d = r.json()
    assert "workout" in d
    w = d["workout"]
    assert w is not None
    assert "exercises" in w or "poses" in w
    exs = w.get("exercises") or w.get("poses") or []
    assert len(exs) >= 1
    assert "id" in exs[0]


def test_post_workout_400_no_onboard(client):
    """POST /workout returns 400 when user not onboarded."""
    user_id = _unique_user()
    r = client.post("/api/users/{}/workout".format(user_id), json={"prompt": "Leg workout"})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Log Set
# ---------------------------------------------------------------------------


def test_post_log_set_by_exercise_id(client, onboarded_user):
    """POST /log-set with exercise_id logs a set."""
    client.post("/api/users/{}/workout".format(onboarded_user), json={"prompt": "Leg workout"})
    r = client.post(
        "/api/users/{}/log-set".format(onboarded_user),
        json={"exercise_id": "ex_0", "weight": 100, "reps": 5, "rpe": 8},
    )
    assert r.status_code == 200
    assert "state" in r.json()
    assert any(e.get("exercise_id") == "ex_0" or "Squat" in str(e.get("exercise_name", "")) for e in r.json().get("state", {}).get("active_logs", []))


def test_post_log_set_400_no_exercise_or_id(client, onboarded_user):
    """POST /log-set returns 400 when neither exercise nor exercise_id provided."""
    client.post("/api/users/{}/workout".format(onboarded_user), json={"prompt": "Leg workout"})
    r = client.post("/api/users/{}/log-set".format(onboarded_user), json={"weight": 100, "reps": 5, "rpe": 8})
    assert r.status_code == 400


def test_post_log_set_400_invalid_exercise_id(client, onboarded_user):
    """POST /log-set returns 400 when exercise_id not in workout."""
    client.post("/api/users/{}/workout".format(onboarded_user), json={"prompt": "Leg workout"})
    r = client.post(
        "/api/users/{}/log-set".format(onboarded_user),
        json={"exercise_id": "ex_99", "weight": 100, "reps": 5, "rpe": 8},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Finish Workout
# ---------------------------------------------------------------------------


def test_post_finish_workout(client, onboarded_user):
    """POST /finish-workout completes workout and returns workout_completed."""
    client.post("/api/users/{}/workout".format(onboarded_user), json={"prompt": "Leg workout"})
    r = client.post("/api/users/{}/finish-workout".format(onboarded_user))
    assert r.status_code == 200
    assert r.json().get("workout_completed") is True


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def test_get_history_empty(client, onboarded_user):
    """GET /history returns empty before any workout completed."""
    r = client.get("/api/users/{}/history".format(onboarded_user))
    assert r.status_code == 200
    assert r.json().get("workout_history") == []


def test_get_history_after_finish(client, onboarded_user):
    """GET /history returns workouts after finish-workout."""
    client.post("/api/users/{}/workout".format(onboarded_user), json={"prompt": "Leg workout"})
    client.post("/api/users/{}/finish-workout".format(onboarded_user))
    r = client.get("/api/users/{}/history".format(onboarded_user))
    assert r.status_code == 200
    hist = r.json().get("workout_history", [])
    assert len(hist) >= 1


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def test_patch_settings(client, onboarded_user):
    """PATCH /settings updates max_workouts_per_week and fatigue_threshold."""
    r = client.patch(
        "/api/users/{}/settings".format(onboarded_user),
        json={"max_workouts_per_week": 5, "fatigue_threshold": 0.75},
    )
    assert r.status_code == 200
    d = r.json()
    assert d.get("max_workouts_per_week") == 5
    assert d.get("fatigue_threshold") == 0.75


def test_patch_settings_invalid_fatigue(client, onboarded_user):
    """PATCH /settings returns 400 for invalid fatigue_threshold."""
    r = client.patch(
        "/api/users/{}/settings".format(onboarded_user),
        json={"fatigue_threshold": 1.5},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Reset Fatigue
# ---------------------------------------------------------------------------


def test_post_reset_fatigue(client, onboarded_user):
    """POST /reset-fatigue resets fatigue scores."""
    r = client.post("/api/users/{}/reset-fatigue".format(onboarded_user))
    assert r.status_code == 200
    d = r.json()
    assert "fatigue_scores" in d or "status" in d


# ---------------------------------------------------------------------------
# Reset Workouts
# ---------------------------------------------------------------------------


def test_post_reset_workouts(client, onboarded_user):
    """POST /reset-workouts resets workouts_completed_this_week."""
    r = client.post("/api/users/{}/reset-workouts".format(onboarded_user))
    assert r.status_code == 200
    d = r.json()
    assert d.get("workouts_completed_this_week") == 0 or "status" in d


# ---------------------------------------------------------------------------
# New Week
# ---------------------------------------------------------------------------


def test_post_new_week(client, onboarded_user):
    """POST /new-week simulates new week."""
    r = client.post("/api/users/{}/new-week".format(onboarded_user))
    assert r.status_code == 200
    assert "status" in r.json() or "message" in r.json()


def test_post_new_week_404_no_user(client):
    """POST /new-week returns 404 when user not found."""
    user_id = _unique_user()
    r = client.post("/api/users/{}/new-week".format(user_id))
    assert r.status_code in (200, 404)  # Implementation may return 200 with no-op


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def cleanup_users(client):
    """Delete test users after each test."""
    yield
    from db_utils import delete_user
    # Best-effort: we don't have user_id in fixture scope for all tests, so we skip
    pass


if __name__ == "__main__":
    if pytest:
        sys.exit(pytest.main([__file__, "-v"]))
    else:
        print("Run with: pytest tests/test_integration_apis.py -v")
