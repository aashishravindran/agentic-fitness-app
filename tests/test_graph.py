"""
Test script for the hierarchical multi-agent graph.

Usage:
    python -m tests.test_graph
    # or from project root: python tests/test_graph.py
"""

import sys
import time
from pathlib import Path

# Ensure project root is on path (tests/ is one level below root)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config  # Load .env first
from graph import run_workout

# Unique prefix per test run so we never load an old/incompatible checkpoint
_TEST_RUN_ID = str(int(time.time() * 1000))


def test_iron_workout():
    """Test Iron Worker (strength training)."""
    print("=" * 70)
    print("Testing Iron Worker (Strength Training)")
    print("=" * 70)

    result = run_workout(
        user_id=f"test_iron_{_TEST_RUN_ID}",
        persona="iron",
        goal="Build strength and muscle mass",
        fatigue_scores={"legs": 0.3, "push": 0.2, "pull": 0.1},
        messages=[{"role": "user", "content": "I want a strength workout focusing on upper body"}],
    )

    workout = result.get("daily_workout", {})
    print(f"\nFocus Area: {workout.get('focus_area', 'N/A')}")
    print(f"Total Exercises: {workout.get('total_exercises', 0)}")
    print(f"\nRationale: {workout.get('overall_rationale', 'N/A')}")

    if "exercises" in workout:
        print("\nExercises:")
        for i, ex in enumerate(workout["exercises"], 1):
            print(f"\n{i}. {ex.get('exercise_name', 'N/A')}")
            print(f"   Sets: {ex.get('sets', 'N/A')} | Reps: {ex.get('reps', 'N/A')}")
            print(f"   Tempo: {ex.get('tempo_notes', 'N/A')}")
            print(f"   Reasoning: {ex.get('iron_justification', 'N/A')}")


def test_yoga_workout():
    """Test Yoga Worker (mobility)."""
    print("\n" + "=" * 70)
    print("Testing Yoga Worker (Mobility)")
    print("=" * 70)

    result = run_workout(
        user_id=f"test_yoga_{_TEST_RUN_ID}",
        persona="yoga",
        goal="Improve flexibility and reduce tension",
        fatigue_scores={"spine": 0.4, "hips": 0.5, "shoulders": 0.3},
        messages=[{"role": "user", "content": "My hips are tight, I need a yoga practice"}],
    )

    workout = result.get("daily_workout", {})
    print(f"\nFocus Area: {workout.get('focus_area', 'N/A')}")
    print(f"Total Duration: {workout.get('total_duration', 'N/A')}")
    print(f"Total Poses: {workout.get('total_poses', 0)}")
    print(f"\nRationale: {workout.get('overall_rationale', 'N/A')}")

    if "poses" in workout:
        print("\nPoses:")
        for i, pose in enumerate(workout["poses"], 1):
            print(f"\n{i}. {pose.get('pose_name', 'N/A')}")
            print(f"   Duration: {pose.get('duration', 'N/A')}")
            print(f"   Focus: {pose.get('focus_area', 'N/A')}")
            print(f"   Reasoning: {pose.get('zen_justification', 'N/A')}")


def test_hiit_workout():
    """Test HIIT Worker (cardio)."""
    print("\n" + "=" * 70)
    print("Testing HIIT Worker (Cardio)")
    print("=" * 70)

    result = run_workout(
        user_id=f"test_hiit_{_TEST_RUN_ID}",
        persona="hiit",
        goal="Improve cardiovascular fitness",
        fatigue_scores={"cardio": 0.2, "cns": 0.3},
        messages=[{"role": "user", "content": "I want a high-intensity cardio session"}],
    )

    workout = result.get("daily_workout", {})
    print(f"\nFocus System: {workout.get('focus_system', 'N/A')}")
    print(f"Total Duration: {workout.get('total_duration', 'N/A')}")
    print(f"Total Exercises: {workout.get('total_exercises', 0)}")
    print(f"\nRationale: {workout.get('overall_rationale', 'N/A')}")

    if "exercises" in workout:
        print("\nExercises:")
        for i, ex in enumerate(workout["exercises"], 1):
            print(f"\n{i}. {ex.get('exercise_name', 'N/A')}")
            print(f"   Work: {ex.get('work_duration', 'N/A')} | Rest: {ex.get('rest_duration', 'N/A')}")
            print(f"   Zone: {ex.get('intensity_zone', 'N/A')} | Rounds: {ex.get('rounds', 'N/A')}")
            print(f"   Reasoning: {ex.get('inferno_justification', 'N/A')}")


def test_kb_workout():
    """Test Kickboxing Worker (coordination)."""
    print("\n" + "=" * 70)
    print("Testing Kickboxing Worker (Combat Fitness)")
    print("=" * 70)

    result = run_workout(
        user_id=f"test_kb_{_TEST_RUN_ID}",
        persona="kickboxing",
        goal="Improve coordination and striking power",
        fatigue_scores={"coordination": 0.2, "speed": 0.3, "endurance": 0.4},
        messages=[{"role": "user", "content": "I want to work on my striking technique"}],
    )

    workout = result.get("daily_workout", {})
    print(f"\nFocus Attribute: {workout.get('focus_attribute', 'N/A')}")
    print(f"Total Duration: {workout.get('total_duration', 'N/A')}")
    print(f"Total Exercises: {workout.get('total_exercises', 0)}")
    print(f"\nRationale: {workout.get('overall_rationale', 'N/A')}")

    if "exercises" in workout:
        print("\nExercises:")
        for i, ex in enumerate(workout["exercises"], 1):
            print(f"\n{i}. {ex.get('exercise_name', 'N/A')}")
            print(f"   Round: {ex.get('round_duration', 'N/A')} | Rest: {ex.get('rest_duration', 'N/A')}")
            print(f"   Intensity: {ex.get('intensity', 'N/A')} | Focus: {ex.get('focus', 'N/A')}")
            print(f"   Rounds: {ex.get('rounds', 'N/A')}")
            print(f"   Reasoning: {ex.get('strikeforce_justification', 'N/A')}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Testing Hierarchical Multi-Agent Fitness System")
    print("=" * 70)
    print("\nPrerequisites:")
    print("1. Run 'python main.py ingest' to populate ChromaDB")
    print("2. Set GOOGLE_API_KEY or OPENAI_API_KEY")
    print("3. Install dependencies: pip install -r requirements.txt")
    print("\n" + "=" * 70 + "\n")

    try:
        test_iron_workout()
        test_yoga_workout()
        test_hiit_workout()
        test_kb_workout()

        print("\n" + "=" * 70)
        print("✅ All Tests Complete")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
