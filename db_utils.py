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
    
    print(f"\nFatigue Scores:")
    fatigue = state.get("fatigue_scores", {})
    if fatigue:
        for muscle, score in sorted(fatigue.items()):
            bar = "█" * int(score * 20)
            print(f"  {muscle:15s}: {score:.2f} {bar}")
    else:
        print("  (none)")
    
    history = state.get("workout_history", [])
    print(f"\nWorkout History: {len(history)} workout(s)")
    if history:
        for i, workout in enumerate(history[-5:], 1):  # Show last 5
            focus = workout.get("focus_area") or workout.get("focus_attribute", "N/A")
            print(f"  {i}. {focus} ({workout.get('total_exercises', '?')} exercises)")
    
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
