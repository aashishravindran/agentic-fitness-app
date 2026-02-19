from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Ensure project root is on path (fixes "No module named 'config'" when run from other dirs)
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config  # Load .env before any agents
from agents.retriever import RetrieverConfig, retrieve_creator_rules
from agents.trainer import trainer_node
from graph import build_graph, run_workout
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
    simulate_new_week,
    migrate_subscribed_personas_all,
)
from ingest import ingest
from state import ExerciseLog, FitnessState, SetLog


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
    """Interactive CLI: chat is the entry point. Run commands start_workout, finish_workout, log_exercise or type natural language."""
    query = (getattr(args, "query", "") or "").strip()
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
    checkpoint_dir = "checkpoints"

    print("=" * 70)
    print("Fitness CLI — Interactive (chat)")
    print("=" * 70)
    print(f"User ID: {user_id} | Persona: {persona} | Goal: {goal}")

    # Optional first query: run once then go into loop
    if query:
        print(f"\nYou: {query}\n")
        try:
            result = run_workout(
                user_id=user_id,
                persona=persona,
                goal=goal,
                fatigue_scores=fatigue_scores,
                messages=[{"role": "user", "content": query}],
                checkpoint_dir=checkpoint_dir,
            )
            workout = result.get("daily_workout")
            workouts_completed = result.get("workouts_completed_this_week", 0)
            max_workouts = result.get("max_workouts_per_week", 4)
            if not workout:
                if workouts_completed >= max_workouts and max_workouts > 0:
                    print("\n🎯 Workout goal achieved for the week! Prioritize rest.\n")
                else:
                    print("No workout generated.")
            else:
                _print_workout(workout, json_out=getattr(args, "json", False))
                if result.get("is_working_out"):
                    print("\n📋 Session paused. Use start_workout, log_exercise <name> <RPE>, finish_workout.")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    try:
        _interactive_chat_loop(user_id, persona, goal, fatigue_scores, checkpoint_dir)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def _get_app_and_config(user_id: str, checkpoint_dir: str = "checkpoints"):
    """Build graph and return (app, config) for the user thread."""
    app = build_graph(checkpoint_dir, enable_persistence=True)
    config = {"configurable": {"thread_id": user_id}}
    return app, config


def _get_state_dict(app, config) -> dict:
    """Get current state dict from app checkpoint."""
    try:
        snap = app.get_state(config)
        values = getattr(snap, "values", snap) if snap else {}
        return values if isinstance(values, dict) else (getattr(values, "__dict__", {}) or {})
    except Exception:
        return {}


def _default_muscle_for_workout(workout: dict) -> str:
    """Infer default muscle group from workout focus."""
    focus = (workout.get("focus_area") or workout.get("focus_system") or workout.get("focus_attribute") or "general").lower()
    if "leg" in focus:
        return "legs"
    if "push" in focus or "chest" in focus:
        return "push"
    if "pull" in focus or "back" in focus:
        return "pull"
    if "spine" in focus:
        return "spine"
    if "hip" in focus:
        return "hips"
    if "shoulder" in focus:
        return "shoulders"
    if "cardio" in focus:
        return "cardio"
    if "cns" in focus:
        return "cns"
    return "general"


def _print_session_status(state: dict, default_persona: str) -> None:
    """Print workouts so far, current persona, and fatigue scores (shown on login and via status/fatigue)."""
    wc = state.get("workouts_completed_this_week", 0)
    mw = state.get("max_workouts_per_week", 4)
    persona = state.get("selected_persona") or default_persona
    fatigue = state.get("fatigue_scores") or {}
    threshold = state.get("fatigue_threshold", 0.8)
    print(f"  Workouts this week: {wc}/{mw}")
    print(f"  Persona: {persona}")
    if fatigue:
        # Show non-zero first, then the rest
        nonzero = {k: v for k, v in fatigue.items() if v > 0}
        other = {k: v for k, v in fatigue.items() if v == 0}
        parts = [f"{k}: {v:.2f}" for k, v in sorted(nonzero.items())] + [f"{k}: {v:.2f}" for k, v in sorted(other.items())]
        print(f"  Fatigue: {', '.join(parts)}")
        if nonzero and max(nonzero.values()) > threshold:
            print(f"  ⚠️  Max fatigue above threshold ({threshold}) — recovery may be suggested.")
    else:
        print("  Fatigue: (none recorded)")
    print()


def _interactive_chat_loop(
    user_id: str,
    persona: str,
    goal: str,
    fatigue_defaults: dict,
    checkpoint_dir: str = "checkpoints",
) -> None:
    """REPL: accept natural language or commands start_workout, finish_workout, log_exercise, fatigue, new_week, quit."""
    app, config = _get_app_and_config(user_id, checkpoint_dir)
    # Show session status on login
    state = _get_state_dict(app, config)
    print("\n--- Session ---")
    _print_session_status(state, persona)
    print("Commands: start_workout | finish_workout | log_exercise [name] [RPE] | fatigue | new_week | quit")
    print("Or type a natural language request (e.g. 'I want a leg workout').\n")
    while True:
        try:
            line = input("> ").strip()
            if not line:
                continue
            low = line.lower()
            # --- start_workout
            if low in ("start_workout", "start", "show"):
                state = _get_state_dict(app, config)
                workout = state.get("daily_workout")
                if not workout:
                    print("No active workout. Type a request (e.g. 'I want a strength workout') to generate one.")
                    continue
                print()
                _print_workout(workout, json_out=False)
                print("\nUse log_exercise <name> <RPE> to log, then finish_workout when done.")
                continue
            # --- finish_workout
            if low in ("finish_workout", "finish", "done"):
                result = app.invoke(None, config)
                print("Workout finalized and saved.")
                wc = result.get("workouts_completed_this_week", 0)
                mw = result.get("max_workouts_per_week", 4)
                if mw:
                    print(f"Weekly progress: {wc}/{mw}")
                continue
            # --- log_exercise: one exercise + score (RPE). e.g. log_exercise "Bench Press" 8 or log Bench 8
            if low.startswith("log_exercise") or low == "log" or low.startswith("log "):
                tokens = line.split()
                if low.startswith("log_exercise"):
                    rest = " ".join(tokens[1:]).strip() if len(tokens) > 1 else ""
                else:
                    rest = " ".join(tokens[1:]).strip() if len(tokens) > 1 else ""
                exercise_name = None
                rpe_val = None
                if rest:
                    parts = rest.strip().split()
                    if len(parts) >= 2:
                        # "Bench Press" 8 or Bench 8
                        try:
                            rpe_val = int(parts[-1])
                            exercise_name = " ".join(parts[:-1]).strip().strip('"\'')
                        except ValueError:
                            pass
                    elif len(parts) == 1:
                        try:
                            rpe_val = int(parts[0])
                        except ValueError:
                            exercise_name = parts[0]
                if not exercise_name:
                    exercise_name = input("Exercise name? ").strip() or "Unknown"
                if rpe_val is None:
                    rpe_s = input("RPE (1-10)? ").strip() or "5"
                    try:
                        rpe_val = max(1, min(10, int(rpe_s)))
                    except ValueError:
                        rpe_val = 5
                state = _get_state_dict(app, config)
                workout = state.get("daily_workout")
                if not workout:
                    print("No active workout. Generate one first (e.g. 'I want a strength workout').")
                    continue
                default_muscle = _default_muscle_for_workout(workout)
                active_logs = list(state.get("active_logs") or [])
                found = False
                for entry in active_logs:
                    if (entry.get("exercise_name") or "").strip().lower() == exercise_name.strip().lower():
                        sets_list = entry.get("sets") or []
                        sets_list.append({"weight": 0.0, "reps": 0, "rpe": rpe_val})
                        entry["sets"] = sets_list
                        entry["average_rpe"] = round(sum(s.get("rpe", 5) for s in sets_list) / len(sets_list), 2)
                        found = True
                        break
                if not found:
                    active_logs.append({
                        "exercise_name": exercise_name.strip(),
                        "muscle_group": default_muscle,
                        "sets": [{"weight": 0.0, "reps": 0, "rpe": rpe_val}],
                        "average_rpe": float(rpe_val),
                    })
                app.update_state(config, {"active_logs": active_logs})
                print(f"Logged {exercise_name} RPE {rpe_val}.")
                continue
            # --- fatigue (view fatigue scores)
            if low in ("fatigue", "scores", "status"):
                state = _get_state_dict(app, config)
                print("--- Fatigue & status ---")
                _print_session_status(state, persona)
                continue
            # --- new_week (simulate new week) — reset counter, set last session 7d ago, apply 7d decay to fatigue
            if low in ("new_week", "new week"):
                state = _get_state_dict(app, config)
                fatigue = state.get("fatigue_scores") or {}
                decay_factor = 0.97
                hours_week = 168  # 7 days
                decayed_scores = {k: max(0.0, v * (decay_factor ** hours_week)) for k, v in fatigue.items()}
                app.update_state(
                    config,
                    {
                        "workouts_completed_this_week": 0,
                        "last_session_timestamp": time.time() - (7 * 24 * 3600),
                        "fatigue_scores": decayed_scores,
                    },
                )
                print("✅ New week applied (counter reset, fatigue decayed as if 7 days passed).")
                state = _get_state_dict(app, config)
                _print_session_status(state, persona)
                continue
            # --- quit
            if low in ("quit", "exit", "q"):
                print("Bye.")
                return
            # --- natural language: run workout or Q&A
            messages = [{"role": "user", "content": line}]
            result = run_workout(
                user_id=user_id,
                persona=persona,
                goal=goal,
                fatigue_scores=fatigue_defaults,
                messages=messages,
                checkpoint_dir=checkpoint_dir,
            )
            # Q&A response (question routed to qa_worker)
            chat_response = result.get("chat_response")
            if chat_response:
                print(f"\nMax: {chat_response}\n")
                continue
            workout = result.get("daily_workout")
            workouts_completed = result.get("workouts_completed_this_week", 0)
            max_workouts = result.get("max_workouts_per_week", 4)
            if not workout:
                if workouts_completed >= max_workouts and max_workouts > 0:
                    print("\nWorkout goal achieved for the week! Prioritize rest.\n")
                else:
                    print("No workout generated.")
                continue
            _print_workout(workout, json_out=False)
            if result.get("is_working_out"):
                print("\nSession paused. Use start_workout to view, log_exercise <name> <RPE> to log, finish_workout when done.")
        except EOFError:
            print("\nBye.")
            return
        except KeyboardInterrupt:
            print("\nBye.")
            return
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


def cmd_start_workout(args: argparse.Namespace) -> None:
    """Resume the current thread and display the generated workout (after chat/train)."""
    user_id = getattr(args, "user_id", "cli_user")
    app, config = _get_app_and_config(user_id)
    try:
        state_snapshot = app.get_state(config)
        values = getattr(state_snapshot, "values", state_snapshot) if state_snapshot else {}
        if isinstance(values, dict):
            state = values
        else:
            state = getattr(values, "__dict__", {}) or {}
        workout = state.get("daily_workout")
        if not workout:
            print("No active workout found. Run: python main.py chat \"I want a workout\" --user-id", user_id, "first.")
            return
        print("=" * 70)
        print("Current workout (log with: python main.py log-exercise --user-id", user_id + ")")
        print("=" * 70)
        _print_workout(workout, json_out=False)
        print("\nTo log sets: python main.py log-exercise --user-id", user_id)
        print("When done:   python main.py finish-workout --user-id", user_id)
    except Exception as e:
        print("Error loading state:", e)


def cmd_log_exercise(args: argparse.Namespace) -> None:
    """Prompt for each exercise: sets, then weight/reps/RPE per set; inject active_logs into state."""
    user_id = getattr(args, "user_id", "cli_user")
    app, config = _get_app_and_config(user_id)
    try:
        state_snapshot = app.get_state(config)
        values = getattr(state_snapshot, "values", state_snapshot) if state_snapshot else {}
        state = values if isinstance(values, dict) else (getattr(values, "__dict__", {}) or {})
        workout = state.get("daily_workout")
        if not workout:
            print("No active workout. Generate one with: python main.py chat \"I want a workout\" --user-id", user_id)
            return
        # Collect exercise names and default muscle group from workout focus
        focus = (workout.get("focus_area") or workout.get("focus_system") or workout.get("focus_attribute") or "general").lower()
        if "leg" in focus:
            default_muscle = "legs"
        elif "push" in focus or "chest" in focus:
            default_muscle = "push"
        elif "pull" in focus or "back" in focus:
            default_muscle = "pull"
        elif "spine" in focus or "hip" in focus:
            default_muscle = "spine" if "spine" in focus else "hips"
        elif "shoulder" in focus:
            default_muscle = "shoulders"
        elif "cardio" in focus or "cns" in focus:
            default_muscle = "cardio" if "cardio" in focus else "cns"
        else:
            default_muscle = "general"
        items = []
        if "exercises" in workout and workout["exercises"]:
            for ex in workout["exercises"]:
                items.append((ex.get("exercise_name", "?"), ex.get("focus_area") or default_muscle))
        elif "poses" in workout and workout["poses"]:
            for p in workout["poses"]:
                items.append((p.get("pose_name", "?"), (p.get("focus_area") or default_muscle).lower()))
        else:
            print("No exercises/poses in this workout.")
            return
        active_logs = []
        for i, (name, muscle_group) in enumerate(items, 1):
            print(f"\n--- Exercise {i}: {name} (muscle_group: {muscle_group}) ---")
            try:
                n_sets = int(input("Number of sets (e.g. 3): ").strip() or "1")
            except ValueError:
                n_sets = 1
            sets_log = []
            for s in range(n_sets):
                w = input(f"  Set {s+1} weight (kg): ").strip()
                r = input(f"  Set {s+1} reps: ").strip()
                rpe_s = input(f"  Set {s+1} RPE (1-10): ").strip()
                weight = float(w) if w else 0.0
                reps = int(r) if r else 0
                rpe = int(rpe_s) if rpe_s else 5
                rpe = max(1, min(10, rpe))
                sets_log.append({"weight": weight, "reps": reps, "rpe": rpe})
            avg_rpe = sum(x["rpe"] for x in sets_log) / len(sets_log) if sets_log else 0.0
            active_logs.append({
                "exercise_name": name,
                "muscle_group": muscle_group,
                "sets": sets_log,
                "average_rpe": round(avg_rpe, 2),
            })
        app.update_state(config, {"active_logs": active_logs})
        print("\nLogs saved. Run: python main.py finish-workout --user-id", user_id)
    except Exception as e:
        print("Error:", e)
        import traceback
        traceback.print_exc()


def cmd_finish_workout(args: argparse.Namespace) -> None:
    """Aggregate logs, compute RPE-based fatigue, save to history, and resume graph to end."""
    user_id = getattr(args, "user_id", "cli_user")
    app, config = _get_app_and_config(user_id)
    try:
        result = app.invoke(None, config)
        workout = result.get("daily_workout")
        print("Workout finalized and saved.")
        if result.get("workout_history"):
            print("Weekly progress:", result.get("workouts_completed_this_week", 0), "/", result.get("max_workouts_per_week", 4))
        if workout:
            print("Focus:", workout.get("focus_area") or workout.get("focus_system") or workout.get("focus_attribute"))
    except Exception as e:
        print("Error finishing workout:", e)
        import traceback
        traceback.print_exc()


def cmd_ask(args: argparse.Namespace) -> None:
    """One-shot Q&A: ask Max a question about your workouts, goals, or fatigue."""
    from agents.qa_agent import run_qa_standalone
    from db_utils import get_user_state

    user_state = get_user_state(args.user_id) or {}
    question = args.question
    print(f"\nYou: {question}\n")
    try:
        answer = run_qa_standalone(user_state, question)
        print(f"Max: {answer}\n")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def cmd_onboard(args: argparse.Namespace) -> None:
    """Run persona recommender for a user and print the recommendation."""
    from graph import run_intake

    user_id = args.user_id
    print("=" * 70)
    print("Onboarding — Persona Recommender")
    print("=" * 70)
    print(f"User:          {user_id}")
    print(f"Height:        {args.height} cm")
    print(f"Weight:        {args.weight} kg")
    print(f"Fitness level: {args.fitness_level}")
    if args.about_me:
        print(f"About me:      {args.about_me}")
    print("\nRunning recommender...\n")

    try:
        result = run_intake(
            user_id=user_id,
            height_cm=float(args.height),
            weight_kg=float(args.weight),
            fitness_level=args.fitness_level,
            about_me=args.about_me or "",
        )
        personas = result.get("recommended_personas") or []
        rationale = result.get("recommendation_rationale") or ""
        subscribed = result.get("subscribed_personas") or []
        print("=" * 70)
        print("RECOMMENDATION")
        print("=" * 70)
        print(f"Recommended personas:  {', '.join(personas) if personas else '(none)'}")
        print(f"Subscribed to:         {', '.join(subscribed) if subscribed else '(none)'}")
        if rationale:
            print(f"\nRationale:\n  {rationale}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def cmd_reset_workout(args: argparse.Namespace) -> None:
    """Clear the current in-progress workout for this user so you can start a new one. Keeps history, fatigue, and settings."""
    user_id = getattr(args, "user_id", "cli_user")
    app, config = _get_app_and_config(user_id)
    try:
        app.update_state(
            config,
            {"daily_workout": None, "active_logs": [], "is_working_out": False},
        )
        app.invoke(None, config)  # run finalize (no-op when no workout) so graph reaches END
        print("Workout reset for", user_id + ". You can run chat again to get a new workout.")
    except Exception as e:
        print("Error resetting workout:", e)
        import traceback
        traceback.print_exc()


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

    elif args.db_cmd == "new-week":
        if simulate_new_week(args.user_id):
            print(f"✅ Simulated new week for {args.user_id}")
            print("   (workouts_completed_this_week = 0, last_session = 7 days ago)")
            print("   Next chat will apply a week of fatigue decay.")
            view_user_state(args.user_id)
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

    elif args.db_cmd == "migrate-subscriptions":
        print("Running subscribed_personas migration for all users...")
        results = migrate_subscribed_personas_all()
        migrated = [u for u, r in results.items() if r.startswith("migrated")]
        already = [u for u, r in results.items() if r == "already_set"]
        errors  = {u: r for u, r in results.items() if r.startswith("error")}
        print(f"\nMigrated ({len(migrated)}):  {', '.join(migrated) if migrated else 'none'}")
        print(f"Already set ({len(already)}): {', '.join(already) if already else 'none'}")
        if errors:
            print(f"Errors ({len(errors)}):")
            for u, e in errors.items():
                print(f"  {u}: {e}")


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
        help="Interactive CLI: optional initial request, then commands start_workout, finish_workout, log_exercise",
    )
    p_chat.add_argument(
        "query",
        nargs="?",
        default="",
        help="Optional first request (e.g. 'I want a leg workout'); then enter interactive loop",
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

    # v1 Workout logging (after chat generates a workout, graph pauses; log then finish)
    p_start = sub.add_parser("start-workout", help="Show current generated workout (after chat)")
    p_start.add_argument("--user-id", default="cli_user", help="User ID (thread)")
    p_start.set_defaults(func=cmd_start_workout)

    p_log = sub.add_parser("log-exercise", help="Log sets (weight, reps, RPE) for each exercise")
    p_log.add_argument("--user-id", default="cli_user", help="User ID (thread)")
    p_log.set_defaults(func=cmd_log_exercise)

    p_finish = sub.add_parser("finish-workout", help="Save logs, apply RPE fatigue, and end session")
    p_finish.add_argument("--user-id", default="cli_user", help="User ID (thread)")
    p_finish.set_defaults(func=cmd_finish_workout)

    p_reset = sub.add_parser("reset-workout", help="Clear current workout for user; keeps history and settings")
    p_reset.add_argument("--user-id", default="cli_user", help="User ID (thread)")
    p_reset.set_defaults(func=cmd_reset_workout)

    p_ask = sub.add_parser("ask", help="One-shot Q&A: ask Max about your workouts, goals, or fatigue")
    p_ask.add_argument("question", help="Your question, e.g. \"How many workouts do I have left this week?\"")
    p_ask.add_argument("--user-id", default="cli_user", help="User ID (loads your state for context)")
    p_ask.set_defaults(func=cmd_ask)

    p_onboard = sub.add_parser("onboard", help="Run persona recommender for a new (or existing) user")
    p_onboard.add_argument("--user-id", default="test_user", help="User ID (creates or resets their profile)")
    p_onboard.add_argument("--height", type=float, required=True, help="Height in cm (e.g. 175)")
    p_onboard.add_argument("--weight", type=float, required=True, help="Weight in kg (e.g. 75)")
    p_onboard.add_argument(
        "--fitness-level",
        default="Intermediate",
        choices=["Beginner", "Intermediate", "Advanced"],
        help="Self-reported fitness level",
    )
    p_onboard.add_argument("--about-me", default="", help="Free-text personal context for hyper-personalised recommendation")
    p_onboard.set_defaults(func=cmd_onboard)

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

    p_db_new_week = db_sub.add_parser("new-week", help="Simulate new week: reset counter + 7-day decay on next run")
    p_db_new_week.add_argument("user_id", help="User ID")
    
    p_db_delete = db_sub.add_parser("delete", help="Delete user from database")
    p_db_delete.add_argument("user_id", help="User ID to delete")
    
    p_db_export = db_sub.add_parser("export", help="Export user state to JSON")
    p_db_export.add_argument("user_id", help="User ID")
    p_db_export.add_argument("output", help="Output JSON file path")

    db_sub.add_parser(
        "migrate-subscriptions",
        help="One-time migration: populate subscribed_personas from selected_persona for all users",
    )

    p_db.set_defaults(func=cmd_db)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()


