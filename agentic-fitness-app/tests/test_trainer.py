"""
Test script for the Trainer Agent.
Run this to verify the trainer_node works with the RAG system.

Usage:
    python -m tests.test_trainer
    # or from project root: python tests/test_trainer.py

Prerequisites:
    1. Run `python main.py ingest` first to populate ChromaDB
    2. Have Ollama running with a model (or set OPENAI_API_KEY)
    3. Install dependencies: pip install -r requirements.txt

Quick Start:
    # Step 1: Ingest creator data
    python main.py ingest

    # Step 2: Run this test
    python -m tests.test_trainer
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on path (tests/ is one level below root)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config  # Load .env first
from agents.trainer import trainer_node
from state import FitnessState


async def test_trainer():
    """Test the trainer agent with sample state."""
    # Sample state matching FitnessState TypedDict
    state: FitnessState = {
        "user_id": "test_user_123",
        "selected_creator": "coach_iron",
        "goal": "Build strength and muscle mass",
        "fatigue_scores": {
            "legs": 0.8,  # High fatigue - should trigger adaptation
            "push": 0.2,
            "pull": 0.3,
            "core": 0.1,
        },
        "retrieved_rules": [],  # Will be fetched by trainer_node
        "retrieved_philosophy": "",
        "current_workout": None,
        "daily_workout": None,
        "is_approved": False,
    }

    print("=" * 70)
    print("Testing Trainer Agent with High Leg Fatigue")
    print("=" * 70)
    print(f"Fatigue Scores: {state['fatigue_scores']}")
    print(f"Goal: {state['goal']}")
    print(f"Creator: {state['selected_creator']}")
    print("\n⚠️  Note: Legs have high fatigue (0.8) - agent should adapt!")
    print("Generating workout...\n")

    try:
        # Run trainer node
        updated_state = await trainer_node(state)

        # Display results
        print("=" * 70)
        print("WORKOUT GENERATED")
        print("=" * 70)
        print(f"\nFocus Area: {updated_state['daily_workout']['focus_area']}")
        print(f"Total Exercises: {updated_state['daily_workout']['total_exercises']}")
        if updated_state['daily_workout'].get('fatigue_adaptations'):
            print(f"\nFatigue Adaptations: {updated_state['daily_workout']['fatigue_adaptations']}")
        print(f"\nOverall Rationale: {updated_state['daily_workout']['overall_rationale']}")

        print("\n" + "-" * 70)
        print("EXERCISES:")
        print("-" * 70)
        for i, exercise in enumerate(updated_state['daily_workout']['exercises'], 1):
            print(f"\n{i}. {exercise['exercise_name']}")
            print(f"   Sets: {exercise['sets']} | Reps: {exercise['reps']}")
            print(f"   Tempo: {exercise['tempo_notes']}")
            print(f"   Iron Reasoning: {exercise['iron_justification']}")

        print("\n" + "=" * 70)
        print("✅ Trainer Agent Test Complete")
        print("=" * 70)

        # Also show JSON output
        print("\nJSON Output (for frontend):")
        print(updated_state['current_workout'])

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting:")
        print("1. Did you run 'python main.py ingest' first?")
        print("2. Is Ollama running? (or set OPENAI_API_KEY)")
        print("3. Is the creator_db directory populated?")


if __name__ == "__main__":
    asyncio.run(test_trainer())
