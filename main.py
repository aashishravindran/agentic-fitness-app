from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from agents.retriever import RetrieverConfig, retrieve_creator_rules
from agents.trainer import trainer_node
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local Fitness RAG (ingest + query).")
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

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()


