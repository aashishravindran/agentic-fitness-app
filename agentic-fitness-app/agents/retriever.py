from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma


@dataclass(frozen=True)
class RetrieverConfig:
    persist_dir: Path
    collection_name: str = "creator_rules"
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "mxbai-embed-large"


def retrieve_creator_rules(
    *,
    query: str,
    selected_creator: str,
    k: int,
    config: RetrieverConfig,
) -> List[str]:
    """
    Retrieve creator-grounded rules from Chroma, filtered by creator_name metadata.
    Returns a list of page_contents (strings) suitable to put into FitnessState['retrieved_rules'].
    """
    embeddings = OllamaEmbeddings(model=config.embedding_model, base_url=config.ollama_base_url)
    vectorstore = Chroma(
        collection_name=config.collection_name,
        persist_directory=str(config.persist_dir.resolve()),
        embedding_function=embeddings,
    )

    docs = vectorstore.similarity_search(
        query=query,
        k=k,
        filter={"creator_name": selected_creator},
    )
    return [d.page_content for d in docs]


def retrieve_node(
    state: dict,
    *,
    query: Optional[str] = None,
    k: int = 6,
    persist_dir: Optional[str] = None,
    collection_name: str = "creator_rules",
    ollama_base_url: str = "http://localhost:11434",
    embedding_model: str = "mxbai-embed-large",
) -> dict:
    """
    LangGraph-friendly node function (pure dict in/out).
    Expects: state['selected_creator'].
    Sets: state['retrieved_rules'].
    """
    selected_creator = state.get("selected_creator")
    if not selected_creator:
        raise ValueError("state['selected_creator'] is required for retrieval")

    effective_query = query or "Provide the key training rules and programming principles."
    cfg = RetrieverConfig(
        persist_dir=Path(persist_dir) if persist_dir else (Path(__file__).parents[1] / "creator_db"),
        collection_name=collection_name,
        ollama_base_url=ollama_base_url,
        embedding_model=embedding_model,
    )
    rules = retrieve_creator_rules(
        query=effective_query,
        selected_creator=selected_creator,
        k=k,
        config=cfg,
    )
    state["retrieved_rules"] = rules
    return state


