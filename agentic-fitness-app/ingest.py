from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Tuple

from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter


def iter_creator_markdown(creators_dir: Path) -> Iterable[Tuple[str, str]]:
    """Yield (creator_name, markdown_text) from *.md files in creators_dir."""
    for md_path in sorted(creators_dir.glob("*.md")):
        creator_name = md_path.stem
        yield creator_name, md_path.read_text(encoding="utf-8")


def chunk_text(text: str, *, chunk_size: int, chunk_overlap: int) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_text(text)


def ingest(
    *,
    creators_dir: Path,
    persist_dir: Path,
    collection_name: str,
    ollama_base_url: str,
    embedding_model: str,
    chunk_size: int,
    chunk_overlap: int,
) -> int:
    creators_dir = creators_dir.resolve()
    persist_dir = persist_dir.resolve()
    persist_dir.mkdir(parents=True, exist_ok=True)

    embeddings = OllamaEmbeddings(model=embedding_model, base_url=ollama_base_url)
    vectorstore = Chroma(
        collection_name=collection_name,
        persist_directory=str(persist_dir),
        embedding_function=embeddings,
    )

    total_added = 0
    for creator_name, markdown in iter_creator_markdown(creators_dir):
        chunks = chunk_text(markdown, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        if not chunks:
            continue

        metadatas = [
            {"creator_name": creator_name, "source": f"{creator_name}.md", "chunk": i}
            for i in range(len(chunks))
        ]
        ids = [f"{creator_name}:{i}" for i in range(len(chunks))]

        vectorstore.add_texts(texts=chunks, metadatas=metadatas, ids=ids)
        total_added += len(chunks)

    # best-effort persist across langchain/chroma versions
    try:
        vectorstore.persist()
    except Exception:
        pass

    return total_added


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest creator markdown into ChromaDB.")
    parser.add_argument(
        "--creators-dir",
        default=str(Path(__file__).parent / "creators"),
        help="Directory containing creator .md files",
    )
    parser.add_argument(
        "--persist-dir",
        default=str(Path(__file__).parent / "creator_db"),
        help="ChromaDB persist directory",
    )
    parser.add_argument("--collection", default="creator_rules", help="Chroma collection name")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--embed-model", default="mxbai-embed-large", help="Ollama embedding model")
    parser.add_argument("--chunk-size", type=int, default=900, help="Chunk size in characters")
    parser.add_argument("--chunk-overlap", type=int, default=120, help="Chunk overlap in characters")

    args = parser.parse_args()
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


if __name__ == "__main__":
    main()


