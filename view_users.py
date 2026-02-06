#!/usr/bin/env python3
"""
Simple script to view users in the database.
Doesn't require all the agent dependencies.
"""

import sqlite3
from pathlib import Path

def list_users(checkpoint_dir: str = "checkpoints"):
    """List all user IDs in the database."""
    db_path = Path(checkpoint_dir) / "checkpoints.db"
    
    if not db_path.exists():
        print(f"\n❌ Database not found at: {db_path}")
        print("   The database will be created when you first use the app.")
        return []
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT thread_id FROM checkpoints ORDER BY thread_id")
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users
    except Exception as e:
        print(f"\n❌ Error reading database: {e}")
        return []

def view_user_summary(user_id: str, checkpoint_dir: str = "checkpoints"):
    """Show a summary of a user's state."""
    db_path = Path(checkpoint_dir) / "checkpoints.db"
    
    if not db_path.exists():
        print(f"\n❌ Database not found at: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Count checkpoints for this user
        cursor.execute(
            "SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?",
            (user_id,)
        )
        count = cursor.fetchone()[0]
        
        # Get the latest checkpoint
        cursor.execute(
            "SELECT checkpoint FROM checkpoints WHERE thread_id = ? ORDER BY checkpoint_ns DESC LIMIT 1",
            (user_id,)
        )
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            import json
            checkpoint_data = json.loads(result[0])
            state = checkpoint_data.get("channel_values", {})
            
            print(f"\n📊 User: {user_id}")
            print(f"   Checkpoints: {count}")
            print(f"   Workouts this week: {state.get('workouts_completed_this_week', 0)}/{state.get('max_workouts_per_week', 4)}")
            print(f"   Persona: {state.get('selected_persona', 'N/A')}")
            
            fatigue = state.get('fatigue_scores', {})
            if fatigue:
                non_zero = {k: v for k, v in fatigue.items() if v > 0}
                if non_zero:
                    print(f"   Fatigue scores: {non_zero}")
            
            if state.get('daily_workout'):
                print(f"   ✅ Has active workout")
            else:
                print(f"   ⚪ No active workout")
        else:
            print(f"\n❌ User '{user_id}' not found in database")
            
    except Exception as e:
        print(f"\n❌ Error reading user data: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # View specific user
        user_id = sys.argv[1]
        view_user_summary(user_id)
    else:
        # List all users
        users = list_users()
        
        if users:
            print(f"\n✅ Found {len(users)} user(s) in database:\n")
            for user in users:
                print(f"   • {user}")
            print(f"\n💡 To view details: python view_users.py <user_id>")
        else:
            print("\n📭 No users found in database")
            print("   Users will be created when they log in through the UI or CLI")
