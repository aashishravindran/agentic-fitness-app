from __future__ import annotations

import argparse
from pathlib import Path

from agents.retriever import RetrieverConfig, retrieve_creator_rules
from ingest import ingest


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

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()


