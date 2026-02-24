"""
Example: How to call the Trainer Agent directly from Python code.

This shows three ways to use the trainer:
1. Async (recommended for production)
2. Sync wrapper (for simple scripts)
3. Direct agent access (advanced)
"""

import asyncio
from agents.trainer import trainer_node, trainer_node_sync, get_trainer_agent
from state import FitnessState


# ============================================================================
# Method 1: Async (Recommended)
# ============================================================================

async def example_async():
    """Call trainer_node directly with async/await."""
    state: FitnessState = {
        "user_id": "user_123",
        "selected_creator": "coach_iron",
        "goal": "Build strength and muscle mass",
        "fatigue_scores": {
            "legs": 0.8,  # High fatigue
            "push": 0.2,
            "pull": 0.3,
        },
        "retrieved_rules": [],
        "retrieved_philosophy": "",
        "current_workout": None,
        "daily_workout": None,
        "is_approved": False,
    }
    
    # Call trainer directly
    updated_state = await trainer_node(state)
    
    # Access the workout
    workout = updated_state["daily_workout"]
    print(f"Focus Area: {workout['focus_area']}")
    print(f"Exercises: {len(workout['exercises'])}")
    
    return updated_state


# ============================================================================
# Method 2: Sync Wrapper (Simple scripts)
# ============================================================================

def example_sync():
    """Call trainer_node_sync for synchronous code."""
    state: FitnessState = {
        "user_id": "user_123",
        "selected_creator": "coach_iron",
        "goal": "Build strength",
        "fatigue_scores": {"legs": 0.2, "push": 0.1, "pull": 0.1},
        "retrieved_rules": [],
        "retrieved_philosophy": "",
        "current_workout": None,
        "daily_workout": None,
        "is_approved": False,
    }
    
    # Call sync wrapper
    updated_state = trainer_node_sync(state)
    
    return updated_state


# ============================================================================
# Method 3: Direct Agent Access (Advanced)
# ============================================================================

async def example_direct_agent():
    """Access the PydanticAI agent directly for custom prompts."""
    from agents.trainer import WorkoutPlan
    
    agent = get_trainer_agent()
    
    # Custom prompt
    custom_prompt = """
    Current Fatigue: legs: 0.9, push: 0.1
    Creator Rules: Focus on progressive overload, 3-second eccentrics
    User Goal: Recover from leg day
    
    Design a recovery-focused upper body workout.
    """
    
    # Run agent directly
    result = await agent.run(custom_prompt)
    workout_plan: WorkoutPlan = result.data
    
    # Access structured data
    print(f"Focus: {workout_plan.focus_area}")
    for exercise in workout_plan.exercises:
        print(f"- {exercise.exercise_name}: {exercise.sets}x{exercise.reps}")


# ============================================================================
# Run Examples
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Example 1: Async Call")
    print("=" * 70)
    result = asyncio.run(example_async())
    print(f"\n✅ Generated workout with {result['daily_workout']['total_exercises']} exercises\n")
    
    print("=" * 70)
    print("Example 2: Sync Call")
    print("=" * 70)
    result2 = example_sync()
    print(f"✅ Generated workout with {result2['daily_workout']['total_exercises']} exercises\n")
    
    print("=" * 70)
    print("Example 3: Direct Agent Access")
    print("=" * 70)
    asyncio.run(example_direct_agent())
