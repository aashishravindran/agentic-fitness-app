from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is on path (fixes "No module named 'config'" when run from other dirs)
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config  # Load .env before any agents
from agents.retriever import RetrieverConfig, retrieve_creator_rules
from agents.trainer import trainer_node
from graph import run_workout
from db_utils import (
    list_users,
    view_user_state,
    update_user_fatigue,
    update_workouts_completed,
    update_max_workouts,
    update_fatigue_threshold,
    clear_user_history,
    delete_user,
    export_user_state,
)
from ingest import ingest
from state import FitnessState


def cmd_ingest(args: argparse.Namespace) -> None:
    added = ingest(
        creators_dir=Path(args.creators_dir),
        persist_dir=Path(args.persist_dir),
        collection_name=args.collection,
        ollama_base_url=args.ollama_url,
        embedding_model=args.embed_model,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    print(f"Ingested {added} chunks into collection '{args.collection}'.")


def cmd_query(args: argparse.Namespace) -> None:
    cfg = RetrieverConfig(
        persist_dir=Path(args.persist_dir),
        collection_name=args.collection,
        ollama_base_url=args.ollama_url,
        embedding_model=args.embed_model,
    )
    rules = retrieve_creator_rules(
        query=args.query,
        selected_creator=args.creator,
        k=args.k,
        config=cfg,
    )
    if not rules:
        print("No results. Did you run ingest first, and is the creator name correct?")
        return
    print(f"Top {len(rules)} retrieved chunks for creator='{args.creator}':\n")
    for i, r in enumerate(rules, start=1):
        print(f"[{i}]\n{r}\n{'-' * 60}")


def cmd_train(args: argparse.Namespace) -> None:
    """Generate a workout using the Trainer Agent."""
    # Parse fatigue scores from string (format: "legs:0.8,push:0.2,pull:0.3")
    fatigue_scores = {}
    if args.fatigue:
        for pair in args.fatigue.split(","):
            if ":" in pair:
                key, value = pair.split(":", 1)
                fatigue_scores[key.strip()] = float(value.strip())
    
    # Build state
    state: FitnessState = {
        "user_id": args.user_id,
        "selected_creator": args.creator,
        "goal": args.goal,
        "fatigue_scores": fatigue_scores or {"legs": 0.2, "push": 0.2, "pull": 0.2},
        "retrieved_rules": [],
        "retrieved_philosophy": "",
        "current_workout": None,
        "daily_workout": None,
        "is_approved": False,
    }
    
    print("=" * 70)
    print("Generating Workout with Trainer Agent")
    print("=" * 70)
    print(f"Creator: {state['selected_creator']}")
    print(f"Goal: {state['goal']}")
    print(f"Fatigue Scores: {state['fatigue_scores']}")
    print("\nGenerating workout...\n")
    
    try:
        # Run trainer node
        updated_state = asyncio.run(trainer_node(state))
        
        # Display results
        workout = updated_state["daily_workout"]
        print("=" * 70)
        print("WORKOUT GENERATED")
        print("=" * 70)
        print(f"\nFocus Area: {workout['focus_area']}")
        print(f"Total Exercises: {workout['total_exercises']}")
        if workout.get("fatigue_adaptations"):
            print(f"\nFatigue Adaptations: {workout['fatigue_adaptations']}")
        print(f"\nOverall Rationale: {workout['overall_rationale']}")
        
        print("\n" + "-" * 70)
        print("EXERCISES:")
        print("-" * 70)
        for i, exercise in enumerate(workout["exercises"], 1):
            print(f"\n{i}. {exercise['exercise_name']}")
            print(f"   Sets: {exercise['sets']} | Reps: {exercise['reps']}")
            print(f"   Tempo: {exercise['tempo_notes']}")
            print(f"   Iron Reasoning: {exercise['iron_justification']}")
        
        # Output JSON if requested
        if args.json:
            print("\n" + "=" * 70)
            print("JSON Output:")
            print("=" * 70)
            print(json.dumps(workout, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting:")
        print("1. Did you run 'python main.py ingest' first?")
        print("2. Is Ollama running? (or set OPENAI_API_KEY)")
        print("3. Is the creator_db directory populated?")


def _parse_fatigue(s: str) -> dict:
    """Parse 'legs:0.8,push:0.2' into {'legs': 0.8, 'push': 0.2}."""
    out = {}
    if not s:
        return out
    for pair in s.split(","):
        if ":" in pair:
            k, v = pair.split(":", 1)
            out[k.strip()] = float(v.strip())
    return out


def _print_workout(workout: dict, *, json_out: bool = False) -> None:
    """Display workout from any worker (iron, yoga, hiit, kickboxing, recovery)."""
    if json_out:
        print(json.dumps(workout, indent=2))
        return

    # Common fields
    print("=" * 70)
    # Check if this is a recovery plan
    if workout.get("recovery_focus") or workout.get("permission_to_rest"):
        print("RECOVERY PLAN")
    else:
        print("WORKOUT")
    print("=" * 70)
    
    # Recovery-specific fields
    if workout.get("recovery_focus"):
        print(f"\nRecovery Focus: {workout['recovery_focus']}")
    if workout.get("permission_to_rest"):
        print(f"\n💚 {workout['permission_to_rest']}")
    if workout.get("step_goal"):
        print(f"\nStep Goal: {workout['step_goal']} steps (NEAT activity)")
    
    # Regular workout fields
    focus = workout.get("focus_area") or workout.get("focus_system") or workout.get("focus_attribute")
    if focus:
        print(f"\nFocus: {focus}")
    if workout.get("total_duration"):
        print(f"Duration: {workout['total_duration']}")
    if workout.get("fatigue_adaptations"):
        print(f"\nFatigue adaptations: {workout['fatigue_adaptations']}")
    if workout.get("overall_rationale"):
        print(f"\nRationale: {workout['overall_rationale']}")

    # Iron / HIIT / Kickboxing: exercises
    if "exercises" in workout and workout["exercises"]:
        exs = workout["exercises"]
        print("\n" + "-" * 70)
        print("EXERCISES")
        print("-" * 70)
        for i, e in enumerate(exs, 1):
            name = e.get("exercise_name", "?")
            sets = e.get("sets")
            reps = e.get("reps")
            tempo = e.get("tempo_notes", "")
            just = e.get("iron_justification") or e.get("inferno_justification") or e.get("strikeforce_justification", "")
            work = e.get("work_duration")
            rest_dur = e.get("rest_duration")
            zone = e.get("intensity_zone") or e.get("intensity", "")
            rounds = e.get("rounds")
            print(f"\n{i}. {name}")
            if sets is not None and reps:
                print(f"   Sets: {sets} | Reps: {reps}")
            if work and rest_dur:
                print(f"   Work: {work} | Rest: {rest_dur}")
            if zone:
                print(f"   Intensity: {zone}")
            if rounds is not None:
                print(f"   Rounds: {rounds}")
            if tempo:
                print(f"   Tempo: {tempo}")
            if just:
                print(f"   Why: {just}")

    # Yoga: poses
    if "poses" in workout and workout["poses"]:
        print("\n" + "-" * 70)
        print("POSES")
        print("-" * 70)
        for i, p in enumerate(workout["poses"], 1):
            name = p.get("pose_name", "?")
            dur = p.get("duration", "")
            focus_p = p.get("focus_area", "")
            just = p.get("zen_justification", "")
            print(f"\n{i}. {name}")
            if dur:
                print(f"   Duration: {dur}")
            if focus_p:
                print(f"   Focus: {focus_p}")
            if just:
                print(f"   Why: {just}")
    
    # Recovery: activities
    if "activities" in workout and workout["activities"]:
        print("\n" + "-" * 70)
        print("RECOVERY ACTIVITIES")
        print("-" * 70)
        for i, a in enumerate(workout["activities"], 1):
            name = a.get("activity_name", "?")
            activity_type = a.get("activity_type", "")
            dur = a.get("duration", "")
            intensity = a.get("intensity", "")
            rationale = a.get("rationale", "")
            print(f"\n{i}. {name}")
            if activity_type:
                print(f"   Type: {activity_type}")
            if dur:
                print(f"   Duration: {dur}")
            if intensity:
                print(f"   Intensity: {intensity}")
            if rationale:
                print(f"   Why: {rationale}")

    print("\n" + "=" * 70)


def cmd_chat(args: argparse.Namespace) -> None:
    """CLI: natural language query → Supervisor → workers → workout."""
    query = (getattr(args, "query", "") or "").strip()
    if not query:
        print("Usage: python main.py chat \"<your request>\"")
        print("Example: python main.py chat \"I want a strength workout, my legs are a bit sore\"")
        print("Example: python main.py chat \"Give me a yoga flow, my hips are tight\"")
        print("Example: python main.py chat \"HIIT session please\" --persona hiit")
        print("\n💡 Tip: Use --user-id to maintain persistent state across sessions")
        return

    defaults = {
        "legs": 0.2, "push": 0.2, "pull": 0.2,
        "spine": 0.1, "hips": 0.1, "shoulders": 0.1,
        "cardio": 0.1, "cns": 0.1,
        "coordination": 0.1, "speed": 0.1, "endurance": 0.1,
    }
    fatigue_scores = {**defaults, **_parse_fatigue(getattr(args, "fatigue", "") or "")}
    persona = args.persona
    goal = args.goal
    user_id = args.user_id

    messages = [{"role": "user", "content": query}]

    print("=" * 70)
    print("Fitness CLI — Supervisor + Agents")
    print("=" * 70)
    print(f"\nYou: {query}")
    print(f"\nUser ID: {user_id} (persistent state)")
    print(f"Persona: {persona} | Goal: {goal}")
    
    # Check if history exists (by trying to load state)
    from pathlib import Path
    checkpoint_dir = Path("checkpoints")
    db_path = checkpoint_dir / "checkpoints.db"
    if db_path.exists():
        print("📚 Loading workout history and fatigue state...")
    else:
        print("🆕 New user - starting fresh (history will be saved)")
    
    print("\nRouting and generating workout...\n")

    try:
        result = run_workout(
            user_id=user_id,
            persona=persona,
            goal=goal,
            fatigue_scores=fatigue_scores,
            messages=messages,
        )
        workout = result.get("daily_workout")
        if not workout:
            print("No workout generated. Supervisor may have routed to 'end'.")
            return
        
        # Show history and safety info
        history = result.get("workout_history", [])
        workouts_completed = result.get("workouts_completed_this_week", 0)
        max_workouts = result.get("max_workouts_per_week", 4)
        fatigue_threshold = result.get("fatigue_threshold", 0.8)
        
        if history:
            print(f"📊 Workout History: {len(history)} previous workout(s)")
            if len(history) > 1:
                print(f"   (Previous workout analyzed for fatigue adjustments)")
        
        print(f"📅 Weekly Progress: {workouts_completed}/{max_workouts} workouts completed")
        if workouts_completed >= max_workouts:
            print("   ⚠️  Weekly limit reached - rest recommended")
        print()
        
        _print_workout(workout, json_out=args.json)
        
        # Show updated fatigue and safety warnings
        final_fatigue = result.get("fatigue_scores", {})
        max_fatigue = max(final_fatigue.values()) if final_fatigue else 0.0
        high_fatigue = {k: v for k, v in final_fatigue.items() if v > 0.5}
        
        if high_fatigue:
            print(f"\n⚠️  Current Fatigue Levels: {', '.join([f'{k}: {v:.2f}' for k, v in high_fatigue.items()])}")
        
        if max_fatigue > fatigue_threshold:
            print(f"\n🚨 SAFETY ALERT: Max fatigue ({max_fatigue:.2f}) exceeds threshold ({fatigue_threshold:.2f})")
            print("   Recovery or rest is strongly recommended before next training session.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting:")
        print("1. Run 'python main.py ingest' first")
        print("2. Set GOOGLE_API_KEY (or OPENAI_API_KEY) in .env")
        print("3. pip install -r requirements.txt")


def cmd_db(args: argparse.Namespace) -> None:
    """Database management commands."""
    if args.db_cmd == "list":
        users = list_users()
        if users:
            print(f"\nFound {len(users)} user(s) in database:\n")
            for user in users:
                print(f"  - {user}")
        else:
            print("\nNo users found in database")
    
    elif args.db_cmd == "view":
        view_user_state(args.user_id)
    
    elif args.db_cmd == "update-fatigue":
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
    
    elif args.db_cmd == "update-workouts":
        if update_workouts_completed(args.user_id, args.count):
            print(f"✅ Updated workouts_completed_this_week to {args.count} for {args.user_id}")
            view_user_state(args.user_id)
        else:
            print(f"❌ User '{args.user_id}' not found")
    
    elif args.db_cmd == "update-max-workouts":
        if update_max_workouts(args.user_id, args.max):
            print(f"✅ Updated max_workouts_per_week to {args.max} for {args.user_id}")
            view_user_state(args.user_id)
        else:
            print(f"❌ User '{args.user_id}' not found")
    
    elif args.db_cmd == "update-threshold":
        if update_fatigue_threshold(args.user_id, args.threshold):
            print(f"✅ Updated fatigue_threshold to {args.threshold} for {args.user_id}")
            view_user_state(args.user_id)
        else:
            print(f"❌ User '{args.user_id}' not found or invalid threshold")
    
    elif args.db_cmd == "clear-history":
        if clear_user_history(args.user_id):
            print(f"✅ Cleared workout history for {args.user_id}")
        else:
            print(f"❌ User '{args.user_id}' not found")
    
    elif args.db_cmd == "delete":
        confirm = input(f"⚠️  Delete all data for user '{args.user_id}'? (yes/no): ")
        if confirm.lower() == "yes":
            if delete_user(args.user_id):
                print(f"✅ Deleted user {args.user_id}")
            else:
                print(f"❌ User '{args.user_id}' not found")
        else:
            print("Cancelled")
    
    elif args.db_cmd == "export":
        if export_user_state(args.user_id, args.output):
            pass  # Message already printed
        else:
            print(f"❌ User '{args.user_id}' not found")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fitness RAG + Supervisor CLI.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ingest = sub.add_parser("ingest", help="Ingest /creators into local Chroma")
    p_ingest.add_argument(
        "--creators-dir",
        default=str(Path(__file__).parent / "creators"),
        help="Directory containing creator .md files",
    )
    p_ingest.add_argument(
        "--persist-dir",
        default=str(Path(__file__).parent / "creator_db"),
        help="ChromaDB persist directory",
    )
    p_ingest.add_argument("--collection", default="creator_rules", help="Chroma collection name")
    p_ingest.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama base URL")
    p_ingest.add_argument("--embed-model", default="mxbai-embed-large", help="Ollama embedding model")
    p_ingest.add_argument("--chunk-size", type=int, default=900, help="Chunk size in characters")
    p_ingest.add_argument("--chunk-overlap", type=int, default=120, help="Chunk overlap in characters")
    p_ingest.set_defaults(func=cmd_ingest)

    p_query = sub.add_parser("query", help="Query local Chroma with creator filter")
    p_query.add_argument("--creator", default="coach_iron", help="Creator name (file stem)")
    p_query.add_argument("--query", default="What are your key programming rules?", help="Query text")
    p_query.add_argument("--k", type=int, default=6, help="Top-k chunks to return")
    p_query.add_argument(
        "--persist-dir",
        default=str(Path(__file__).parent / "creator_db"),
        help="ChromaDB persist directory",
    )
    p_query.add_argument("--collection", default="creator_rules", help="Chroma collection name")
    p_query.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama base URL")
    p_query.add_argument("--embed-model", default="mxbai-embed-large", help="Ollama embedding model")
    p_query.set_defaults(func=cmd_query)

    p_train = sub.add_parser("train", help="Generate workout using Trainer Agent")
    p_train.add_argument("--creator", default="coach_iron", help="Creator name (file stem)")
    p_train.add_argument("--goal", default="Build strength and muscle mass", help="User fitness goal")
    p_train.add_argument(
        "--fatigue",
        default="legs:0.2,push:0.2,pull:0.2",
        help="Fatigue scores as 'key:value,key:value' (e.g., 'legs:0.8,push:0.2')",
    )
    p_train.add_argument("--user-id", default="user_123", help="User ID")
    p_train.add_argument("--json", action="store_true", help="Output workout as JSON")
    p_train.set_defaults(func=cmd_train)

    p_chat = sub.add_parser(
        "chat",
        help="Natural language query → Supervisor routes to agents, returns workout",
    )
    p_chat.add_argument(
        "query",
        nargs="?",
        default="",
        help="Your request, e.g. 'I want a yoga session, my hips are tight'",
    )
    p_chat.add_argument(
        "--persona",
        default="iron",
        choices=["iron", "yoga", "hiit", "kickboxing"],
        help="Default persona if not inferred from query",
    )
    p_chat.add_argument("--goal", default="Build strength and improve fitness", help="Fitness goal")
    p_chat.add_argument(
        "--fatigue",
        default="",
        help="Fatigue scores, e.g. 'legs:0.7,push:0.2'",
    )
    p_chat.add_argument(
        "--user-id",
        default="cli_user",
        help="User ID for persistent state (same ID = same history across sessions)",
    )
    p_chat.add_argument("--json", action="store_true", help="Output workout as JSON")
    p_chat.set_defaults(func=cmd_chat)

    # Database management commands
    p_db = sub.add_parser("db", help="Database management utilities")
    db_sub = p_db.add_subparsers(dest="db_cmd", required=True)
    
    db_sub.add_parser("list", help="List all users in database")
    
    p_db_view = db_sub.add_parser("view", help="View user state")
    p_db_view.add_argument("user_id", help="User ID to view")
    
    p_db_fatigue = db_sub.add_parser("update-fatigue", help="Update user fatigue scores")
    p_db_fatigue.add_argument("user_id", help="User ID")
    p_db_fatigue.add_argument("fatigue", help="Fatigue scores, e.g. 'legs:0.5,push:0.3'")
    
    p_db_workouts = db_sub.add_parser("update-workouts", help="Update workouts_completed_this_week")
    p_db_workouts.add_argument("user_id", help="User ID")
    p_db_workouts.add_argument("count", type=int, help="Number of workouts completed this week")
    
    p_db_max = db_sub.add_parser("update-max-workouts", help="Update max_workouts_per_week")
    p_db_max.add_argument("user_id", help="User ID")
    p_db_max.add_argument("max", type=int, help="Maximum workouts per week")
    
    p_db_threshold = db_sub.add_parser("update-threshold", help="Update fatigue_threshold")
    p_db_threshold.add_argument("user_id", help="User ID")
    p_db_threshold.add_argument("threshold", type=float, help="Fatigue threshold (0.0 to 1.0, default: 0.8)")
    
    p_db_clear = db_sub.add_parser("clear-history", help="Clear workout history for user")
    p_db_clear.add_argument("user_id", help="User ID")
    
    p_db_delete = db_sub.add_parser("delete", help="Delete user from database")
    p_db_delete.add_argument("user_id", help="User ID to delete")
    
    p_db_export = db_sub.add_parser("export", help="Export user state to JSON")
    p_db_export.add_argument("user_id", help="User ID")
    p_db_export.add_argument("output", help="Output JSON file path")
    
    p_db.set_defaults(func=cmd_db)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()


