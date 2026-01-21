# agentic-fitness-app

## Local Fitness RAG (first milestone)

The RAG system lives in the repo root and supports:

- Ingesting creator markdown files from `creators/`
- Chunking + embedding locally via Ollama (`mxbai-embed-large`)
- Persisting to local ChromaDB (`creator_db/`)
- Querying with a **creator filter** (`creator_name`)

### Setup

- **Install Ollama** and pull the embedding model:
  - `ollama pull mxbai-embed-large`
- **Install Python deps**:
  - `pip install -r requirements.txt`

### Run (ingest + query)

- **Ingest**:
  - `python main.py ingest`
- **Query** (filtered by creator):
  - `python main.py query --creator coach_iron --query "How should I adjust training when fatigue is high?"`

