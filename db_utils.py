"""
Database Utilities for Managing Persistent State

Tools to view, update, and manage the SQLite checkpoint database using LangGraph's API.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try importing SqliteSaver
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    SQLITE_AVAILABLE = True
except ImportError:
    SqliteSaver = None
    SQLITE_AVAILABLE = False


def get_db_path(checkpoint_dir: str = "checkpoints") -> Path:
    """Get the path to the checkpoint database."""
    return Path(checkpoint_dir) / "checkpoints.db"


def get_checkpointer(checkpoint_dir: str = "checkpoints"):
    """Get a SqliteSaver checkpointer instance."""
    if not SQLITE_AVAILABLE:
        raise ImportError("langgraph-checkpoint-sqlite is not installed")
    
    Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
    db_path = get_db_path(checkpoint_dir)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    return SqliteSaver(conn)


def list_users(checkpoint_dir: str = "checkpoints") -> List[str]:
    """
    List all user IDs (thread_ids) in the database.
    
    Args:
        checkpoint_dir: Directory containing the checkpoint database
    
    Returns:
        List of user IDs
    """
    db_path = get_db_path(checkpoint_dir)
    if not db_path.exists():
        return []
    
    # Use SQLite directly for listing (simpler than checkpointer API)
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT thread_id FROM checkpoints")
        users = [row[0] for row in cursor.fetchall()]
        return users
    finally:
        conn.close()


def get_user_state(user_id: str, checkpoint_dir: str = "checkpoints") -> Optional[Dict[str, Any]]:
    """
    Get the current state for a user using LangGraph's checkpointer API.
    
    Args:
        user_id: User ID (thread_id)
        checkpoint_dir: Directory containing the checkpoint database
    
    Returns:
        User state dict or None if not found
    """
    if not SQLITE_AVAILABLE:
        return None
    
    db_path = get_db_path(checkpoint_dir)
    if not db_path.exists():
        return None
    
    checkpointer = get_checkpointer(checkpoint_dir)
    config = {"configurable": {"thread_id": user_id}}
    
    try:
        checkpoint = checkpointer.get(config)
        if checkpoint:
            # Checkpoint might be a dict with channel_values or the state itself
            if isinstance(checkpoint, dict) and "channel_values" in checkpoint:
                return checkpoint["channel_values"]
            elif isinstance(checkpoint, dict):
                # Might be the state directly
                return checkpoint
        return None
    except Exception as e:
        print(f"Error getting user state: {e}")
        return None


def update_user_fatigue(
    user_id: str,
    fatigue_scores: Dict[str, float],
    checkpoint_dir: str = "checkpoints",
) -> bool:
    """
    Update fatigue scores for a user using LangGraph's checkpointer API.
    
    Args:
        user_id: User ID (thread_id)
        fatigue_scores: New fatigue scores dict
        checkpoint_dir: Directory containing the checkpoint database
    
    Returns:
        True if updated, False if user not found
    """
    if not SQLITE_AVAILABLE:
        return False
    
    state = get_user_state(user_id, checkpoint_dir)
    if not state:
        return False
    
    # Update fatigue scores
    state["fatigue_scores"] = fatigue_scores
    
    # Save back using checkpointer API
    checkpointer = get_checkpointer(checkpoint_dir)
    read_config = {"configurable": {"thread_id": user_id}}
    
    try:
        # Get current checkpoint to preserve metadata
        current_checkpoint = checkpointer.get(read_config)
        if not current_checkpoint:
            return False
        
        # Update the state in the checkpoint
        # Copy all fields from current checkpoint and update channel_values
        # This preserves all required fields like 'id', 'checkpoint_ns', etc.
        checkpoint = dict(current_checkpoint)
        checkpoint["channel_values"] = state
        
        # Use empty string as default namespace (LangGraph's default)
        # checkpoint_ns is required by put() method in the config
        write_config = {"configurable": {"thread_id": user_id, "checkpoint_ns": ""}}
        checkpointer.put(write_config, checkpoint, {}, {})
        return True
    except Exception as e:
        print(f"Error updating fatigue: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_workouts_completed(
    user_id: str,
    workouts_completed: int,
    checkpoint_dir: str = "checkpoints",
) -> bool:
    """
    Update workouts_completed_this_week for a user.
    
    Args:
        user_id: User ID (thread_id)
        workouts_completed: New workouts_completed_this_week value
        checkpoint_dir: Directory containing the checkpoint database
    
    Returns:
        True if updated, False if user not found
    """
    if not SQLITE_AVAILABLE:
        return False
    
    state = get_user_state(user_id, checkpoint_dir)
    if not state:
        return False
    
    # Update workouts_completed_this_week
    state["workouts_completed_this_week"] = workouts_completed
    
    # Save back using checkpointer API
    checkpointer = get_checkpointer(checkpoint_dir)
    read_config = {"configurable": {"thread_id": user_id}}
    
    try:
        current_checkpoint = checkpointer.get(read_config)
        if not current_checkpoint:
            return False
        
        # Copy all fields from current checkpoint and update channel_values
        checkpoint = dict(current_checkpoint)
        checkpoint["channel_values"] = state
        
        # Use empty string as default namespace
        write_config = {"configurable": {"thread_id": user_id, "checkpoint_ns": ""}}
        checkpointer.put(write_config, checkpoint, {}, {})
        return True
    except Exception as e:
        print(f"Error updating workouts_completed: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_max_workouts(
    user_id: str,
    max_workouts: int,
    checkpoint_dir: str = "checkpoints",
) -> bool:
    """
    Update max_workouts_per_week for a user.
    
    Args:
        user_id: User ID (thread_id)
        max_workouts: New max_workouts_per_week value
        checkpoint_dir: Directory containing the checkpoint database
    
    Returns:
        True if updated, False if user not found
    """
    if not SQLITE_AVAILABLE:
        return False
    
    state = get_user_state(user_id, checkpoint_dir)
    if not state:
        return False
    
    # Update max_workouts_per_week
    state["max_workouts_per_week"] = max_workouts
    
    # Save back using checkpointer API
    checkpointer = get_checkpointer(checkpoint_dir)
    read_config = {"configurable": {"thread_id": user_id}}
    
    try:
        current_checkpoint = checkpointer.get(read_config)
        if not current_checkpoint:
            return False
        
        # Copy all fields from current checkpoint and update channel_values
        checkpoint = dict(current_checkpoint)
        checkpoint["channel_values"] = state
        
        # Use empty string as default namespace
        write_config = {"configurable": {"thread_id": user_id, "checkpoint_ns": ""}}
        checkpointer.put(write_config, checkpoint, {}, {})
        return True
    except Exception as e:
        print(f"Error updating max_workouts: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_user_profile(
    user_id: str,
    profile_data: Dict[str, Any],
    checkpoint_dir: str = "checkpoints",
) -> bool:
    """
    Persist biometric data (height, weight, fitness_level) and onboarding status.

    Args:
        user_id: User ID (thread_id)
        profile_data: Dict with keys height_cm, weight_kg, fitness_level, is_onboarded, recommended_persona
        checkpoint_dir: Directory containing the checkpoint database

    Returns:
        True if updated, False if user not found
    """
    if not SQLITE_AVAILABLE:
        return False

    state = get_user_state(user_id, checkpoint_dir)
    if not state:
        return False

    for key in ("height_cm", "weight_kg", "fitness_level", "about_me", "is_onboarded", "recommended_persona", "recommended_personas", "recommendation_rationale", "subscribed_personas"):
        if key in profile_data:
            state[key] = profile_data[key]

    return _save_state_to_checkpoint(user_id, state, checkpoint_dir)


def update_selected_persona(
    user_id: str,
    persona: str,
    checkpoint_dir: str = "checkpoints",
) -> bool:
    """
    Store the user's finalized persona choice.

    Args:
        user_id: User ID (thread_id)
        persona: Persona key (iron, yoga, hiit, kickboxing) or creator key (coach_iron, etc.)
        checkpoint_dir: Directory containing the checkpoint database

    Returns:
        True if updated, False if user not found
    """
    if not SQLITE_AVAILABLE:
        return False

    # Map creator keys to persona keys (and vice versa)
    creator_to_persona_map = {
        "coach_iron": "iron",
        "zenflow_yoga": "yoga",
        "inferno_hiit": "hiit",
        "strikeforce_kb": "kickboxing",
    }
    persona_to_creator = {v: k for k, v in creator_to_persona_map.items()}

    if persona in creator_to_persona_map:
        persona_key = creator_to_persona_map[persona]
        creator_key = persona
    else:
        persona_key = persona
        creator_key = persona_to_creator.get(persona, persona)

    state = get_user_state(user_id, checkpoint_dir)
    if not state:
        return False

    state["selected_persona"] = persona_key
    state["selected_creator"] = creator_key

    return _save_state_to_checkpoint(user_id, state, checkpoint_dir)


def update_subscribed_personas(
    user_id: str,
    personas: List[str],
    checkpoint_dir: str = "checkpoints",
) -> bool:
    """
    Store the user's subscribed personas (can be multiple).
    Also sets selected_persona to the first in the list.

    Args:
        user_id: User ID (thread_id)
        personas: List of persona or creator keys (e.g. ["iron", "yoga"] or ["coach_iron", "zenflow_yoga"])
        checkpoint_dir: Directory containing the checkpoint database

    Returns:
        True if updated, False if user not found
    """
    if not SQLITE_AVAILABLE:
        return False

    creator_to_persona_map = {
        "coach_iron": "iron",
        "zenflow_yoga": "yoga",
        "inferno_hiit": "hiit",
        "strikeforce_kb": "kickboxing",
    }
    persona_to_creator = {v: k for k, v in creator_to_persona_map.items()}

    persona_keys: List[str] = []
    creator_keys: List[str] = []
    for p in personas:
        if not p:
            continue
        if p in creator_to_persona_map:
            persona_keys.append(creator_to_persona_map[p])
            creator_keys.append(p)
        else:
            persona_keys.append(p)
            creator_keys.append(persona_to_creator.get(p, p))

    # Deduplicate while preserving order
    seen = set()
    unique_persona = []
    unique_creator = []
    for pk, ck in zip(persona_keys, creator_keys):
        if pk not in seen:
            seen.add(pk)
            unique_persona.append(pk)
            unique_creator.append(ck)

    if not unique_persona:
        return False

    state = get_user_state(user_id, checkpoint_dir)
    if not state:
        return False

    state["subscribed_personas"] = unique_persona
    state["selected_persona"] = unique_persona[0]
    state["selected_creator"] = unique_creator[0]

    return _save_state_to_checkpoint(user_id, state, checkpoint_dir)


def _save_state_to_checkpoint(
    user_id: str,
    state: Dict[str, Any],
    checkpoint_dir: str = "checkpoints",
) -> bool:
    """
    Internal helper to write state back to SQLite checkpoint.

    Returns:
        True if saved, False if checkpoint not found
    """
    if not SQLITE_AVAILABLE:
        return False

    checkpointer = get_checkpointer(checkpoint_dir)
    read_config = {"configurable": {"thread_id": user_id}}

    try:
        current_checkpoint = checkpointer.get(read_config)
        if not current_checkpoint:
            return False

        checkpoint = dict(current_checkpoint)
        checkpoint["channel_values"] = state
        write_config = {"configurable": {"thread_id": user_id, "checkpoint_ns": ""}}
        checkpointer.put(write_config, checkpoint, {}, {})
        return True
    except Exception as e:
        print(f"Error saving state: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_fatigue_threshold(
    user_id: str,
    threshold: float,
    checkpoint_dir: str = "checkpoints",
) -> bool:
    """
    Update fatigue_threshold for a user.
    
    Args:
        user_id: User ID (thread_id)
        threshold: New fatigue_threshold value (0.0 to 1.0)
        checkpoint_dir: Directory containing the checkpoint database
    
    Returns:
        True if updated, False if user not found
    """
    if not SQLITE_AVAILABLE:
        return False
    
    # Validate threshold
    if not (0.0 <= threshold <= 1.0):
        print(f"❌ Fatigue threshold must be between 0.0 and 1.0, got {threshold}")
        return False
    
    state = get_user_state(user_id, checkpoint_dir)
    if not state:
        return False
    
    # Update fatigue_threshold
    state["fatigue_threshold"] = threshold
    
    # Save back using checkpointer API
    checkpointer = get_checkpointer(checkpoint_dir)
    read_config = {"configurable": {"thread_id": user_id}}
    
    try:
        current_checkpoint = checkpointer.get(read_config)
        if not current_checkpoint:
            return False
        
        # Copy all fields from current checkpoint and update channel_values
        checkpoint = dict(current_checkpoint)
        checkpoint["channel_values"] = state
        
        # Use empty string as default namespace
        write_config = {"configurable": {"thread_id": user_id, "checkpoint_ns": ""}}
        checkpointer.put(write_config, checkpoint, {}, {})
        return True
    except Exception as e:
        print(f"Error updating fatigue_threshold: {e}")
        import traceback
        traceback.print_exc()
        return False


def clear_user_history(user_id: str, checkpoint_dir: str = "checkpoints") -> bool:
    """
    Clear workout history for a user (keeps other state).
    
    Args:
        user_id: User ID (thread_id)
        checkpoint_dir: Directory containing the checkpoint database
    
    Returns:
        True if cleared, False if user not found
    """
    if not SQLITE_AVAILABLE:
        return False
    
    state = get_user_state(user_id, checkpoint_dir)
    if not state:
        return False
    
    # Clear history
    state["workout_history"] = []
    
    # Save back using checkpointer API
    checkpointer = get_checkpointer(checkpoint_dir)
    read_config = {"configurable": {"thread_id": user_id}}
    
    try:
        current_checkpoint = checkpointer.get(read_config)
        if not current_checkpoint:
            return False
        
        # Copy all fields from current checkpoint and update channel_values
        # This preserves all required fields like 'id', 'checkpoint_ns', etc.
        checkpoint = dict(current_checkpoint)
        checkpoint["channel_values"] = state
        
        # Use empty string as default namespace (LangGraph's default)
        # checkpoint_ns is required by put() method in the config
        write_config = {"configurable": {"thread_id": user_id, "checkpoint_ns": ""}}
        checkpointer.put(write_config, checkpoint, {}, {})
        return True
    except Exception as e:
        print(f"Error clearing history: {e}")
        import traceback
        traceback.print_exc()
        return False


def simulate_new_week(user_id: str, checkpoint_dir: str = "checkpoints") -> bool:
    """
    Simulate a new week: set workouts_completed_this_week to 0 and set
    last_session_timestamp to 7 days ago. On the next chat run, the decay
    node will see 168+ hours passed and apply a week of fatigue decay.
    
    Args:
        user_id: User ID (thread_id)
        checkpoint_dir: Directory containing the checkpoint database
    
    Returns:
        True if updated, False if user not found
    """
    import time
    if not SQLITE_AVAILABLE:
        return False
    state = get_user_state(user_id, checkpoint_dir)
    if not state:
        return False
    state["workouts_completed_this_week"] = 0
    # 7 days ago so decay node applies a week of decay on next run
    state["last_session_timestamp"] = time.time() - (7 * 24 * 3600)
    checkpointer = get_checkpointer(checkpoint_dir)
    read_config = {"configurable": {"thread_id": user_id}}
    try:
        current_checkpoint = checkpointer.get(read_config)
        if not current_checkpoint:
            return False
        checkpoint = dict(current_checkpoint)
        checkpoint["channel_values"] = state
        write_config = {"configurable": {"thread_id": user_id, "checkpoint_ns": ""}}
        checkpointer.put(write_config, checkpoint, {}, {})
        return True
    except Exception as e:
        print(f"Error simulating new week: {e}")
        import traceback
        traceback.print_exc()
        return False


def migrate_subscribed_personas_all(
    checkpoint_dir: str = "checkpoints",
    default_persona: str = "iron",
) -> Dict[str, str]:
    """
    One-time migration: for every user whose subscribed_personas is null/empty,
    set it from selected_persona (falling back to default_persona).
    Also ensures selected_persona always mirrors subscribed_personas[0].

    Returns a summary dict: {user_id: "migrated" | "already_set" | "error"}.
    """
    users = list_users(checkpoint_dir)
    results: Dict[str, str] = {}
    for user_id in users:
        try:
            state = get_user_state(user_id, checkpoint_dir)
            if not state:
                results[user_id] = "no_state"
                continue

            existing = state.get("subscribed_personas")
            if existing:
                # Already has subscriptions — ensure selected_persona matches [0]
                first = existing[0]
                if state.get("selected_persona") != first:
                    state["selected_persona"] = first
                    state["selected_creator"] = first
                    _save_state_to_checkpoint(user_id, state, checkpoint_dir)
                results[user_id] = "already_set"
                continue

            # Pull from selected_persona or fall back to default
            persona = state.get("selected_persona") or default_persona
            # Validate it's a known persona key
            valid = {"iron", "yoga", "hiit", "kickboxing"}
            if persona not in valid:
                persona = default_persona

            state["subscribed_personas"] = [persona]
            state["selected_persona"] = persona
            _save_state_to_checkpoint(user_id, state, checkpoint_dir)
            results[user_id] = f"migrated→{persona}"
        except Exception as e:
            results[user_id] = f"error:{e}"
    return results


def delete_user(user_id: str, checkpoint_dir: str = "checkpoints") -> bool:
    """
    Delete all data for a user.
    
    Args:
        user_id: User ID (thread_id)
        checkpoint_dir: Directory containing the checkpoint database
    
    Returns:
        True if deleted, False if user not found
    """
    db_path = get_db_path(checkpoint_dir)
    if not db_path.exists():
        return False
    
    # Use SQLite directly for deletion (simpler)
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def view_user_state(user_id: str, checkpoint_dir: str = "checkpoints") -> None:
    """
    Print a formatted view of user state.
    
    Args:
        user_id: User ID (thread_id)
        checkpoint_dir: Directory containing the checkpoint database
    """
    state = get_user_state(user_id, checkpoint_dir)
    if not state:
        print(f"❌ User '{user_id}' not found in database")
        return
    
    print(f"\n{'=' * 70}")
    print(f"User State: {user_id}")
    print(f"{'=' * 70}\n")
    
    print(f"Persona: {state.get('selected_persona', 'N/A')}")
    print(f"Goal: {state.get('goal', 'N/A')}")
    print(f"Last Session: {state.get('last_session_timestamp', 'N/A')}")
    
    # Safety & Frequency Info
    max_workouts = state.get("max_workouts_per_week", 4)
    workouts_completed = state.get("workouts_completed_this_week", 0)
    fatigue_threshold = state.get("fatigue_threshold", 0.8)
    
    print(f"\nSafety Settings:")
    print(f"  Max Workouts/Week: {max_workouts}")
    print(f"  Workouts Completed: {workouts_completed}/{max_workouts}")
    print(f"  Fatigue Threshold: {fatigue_threshold}")
    if workouts_completed >= max_workouts:
        print(f"  ⚠️  Weekly limit reached")
    
    print(f"\nFatigue Scores:")
    fatigue = state.get("fatigue_scores", {})
    if fatigue:
        max_fatigue = max(fatigue.values())
        for muscle, score in sorted(fatigue.items()):
            bar = "█" * int(score * 20)
            warning = " 🚨" if score > fatigue_threshold else ""
            print(f"  {muscle:15s}: {score:.2f} {bar}{warning}")
        if max_fatigue > fatigue_threshold:
            print(f"\n  ⚠️  Max fatigue ({max_fatigue:.2f}) exceeds threshold - recovery recommended")
    else:
        print("  (none)")
    
    history = state.get("workout_history", [])
    print(f"\nWorkout History: {len(history)} workout(s)")
    if history:
        for i, workout in enumerate(history[-5:], 1):  # Show last 5
            focus = workout.get("focus_area") or workout.get("focus_attribute") or workout.get("recovery_focus", "N/A")
            workout_type = "Recovery" if workout.get("recovery_focus") else "Training"
            exercises = workout.get("total_exercises") or workout.get("total_activities", "?")
            print(f"  {i}. [{workout_type}] {focus} ({exercises} items)")
    
    print(f"\n{'=' * 70}\n")


def export_user_state(user_id: str, output_file: str, checkpoint_dir: str = "checkpoints") -> bool:
    """
    Export user state to a JSON file.
    
    Args:
        user_id: User ID (thread_id)
        output_file: Path to output JSON file
        checkpoint_dir: Directory containing the checkpoint database
    
    Returns:
        True if exported, False if user not found
    """
    state = get_user_state(user_id, checkpoint_dir)
    if not state:
        return False
    
    with open(output_file, "w") as f:
        json.dump(state, f, indent=2)
    
    print(f"✅ Exported state to {output_file}")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database utilities for fitness app")
    sub = parser.add_subparsers(dest="cmd", required=True)
    
    # List users
    sub.add_parser("list", help="List all users in database")
    
    # View user
    p_view = sub.add_parser("view", help="View user state")
    p_view.add_argument("user_id", help="User ID to view")
    
    # Update fatigue
    p_fatigue = sub.add_parser("update-fatigue", help="Update user fatigue scores")
    p_fatigue.add_argument("user_id", help="User ID")
    p_fatigue.add_argument("fatigue", help="Fatigue scores, e.g. 'legs:0.5,push:0.3'")
    
    # Update workouts completed
    p_workouts = sub.add_parser("update-workouts", help="Update workouts_completed_this_week")
    p_workouts.add_argument("user_id", help="User ID")
    p_workouts.add_argument("count", type=int, help="Number of workouts completed this week")
    
    # Update max workouts
    p_max = sub.add_parser("update-max-workouts", help="Update max_workouts_per_week")
    p_max.add_argument("user_id", help="User ID")
    p_max.add_argument("max", type=int, help="Maximum workouts per week")
    
    # Update fatigue threshold
    p_threshold = sub.add_parser("update-threshold", help="Update fatigue_threshold")
    p_threshold.add_argument("user_id", help="User ID")
    p_threshold.add_argument("threshold", type=float, help="Fatigue threshold (0.0 to 1.0)")
    
    # Clear history
    p_clear = sub.add_parser("clear-history", help="Clear workout history for user")
    p_clear.add_argument("user_id", help="User ID")
    
    # Delete user
    p_delete = sub.add_parser("delete", help="Delete user from database")
    p_delete.add_argument("user_id", help="User ID to delete")
    
    # Export
    p_export = sub.add_parser("export", help="Export user state to JSON")
    p_export.add_argument("user_id", help="User ID")
    p_export.add_argument("output", help="Output JSON file path")
    
    args = parser.parse_args()
    
    if args.cmd == "list":
        users = list_users()
        if users:
            print(f"\nFound {len(users)} user(s):\n")
            for user in users:
                print(f"  - {user}")
        else:
            print("\nNo users found in database")
    
    elif args.cmd == "view":
        view_user_state(args.user_id)
    
    elif args.cmd == "update-fatigue":
        # Parse fatigue scores
        fatigue_dict = {}
        for pair in args.fatigue.split(","):
            if ":" in pair:
                key, value = pair.split(":", 1)
                fatigue_dict[key.strip()] = float(value.strip())
        
        if update_user_fatigue(args.user_id, fatigue_dict):
            print(f"✅ Updated fatigue for {args.user_id}")
            view_user_state(args.user_id)
        else:
            print(f"❌ User '{args.user_id}' not found")
    
    elif args.cmd == "update-workouts":
        if update_workouts_completed(args.user_id, args.count):
            print(f"✅ Updated workouts_completed_this_week to {args.count} for {args.user_id}")
            view_user_state(args.user_id)
        else:
            print(f"❌ User '{args.user_id}' not found")
    
    elif args.cmd == "update-max-workouts":
        if update_max_workouts(args.user_id, args.max):
            print(f"✅ Updated max_workouts_per_week to {args.max} for {args.user_id}")
            view_user_state(args.user_id)
        else:
            print(f"❌ User '{args.user_id}' not found")
    
    elif args.cmd == "update-threshold":
        if update_fatigue_threshold(args.user_id, args.threshold):
            print(f"✅ Updated fatigue_threshold to {args.threshold} for {args.user_id}")
            view_user_state(args.user_id)
        else:
            print(f"❌ User '{args.user_id}' not found or invalid threshold")
    
    elif args.cmd == "clear-history":
        if clear_user_history(args.user_id):
            print(f"✅ Cleared history for {args.user_id}")
        else:
            print(f"❌ User '{args.user_id}' not found")
    
    elif args.cmd == "delete":
        if delete_user(args.user_id):
            print(f"✅ Deleted user {args.user_id}")
        else:
            print(f"❌ User '{args.user_id}' not found")
    
    elif args.cmd == "export":
        if export_user_state(args.user_id, args.output):
            pass  # Message already printed
        else:
            print(f"❌ User '{args.user_id}' not found")
