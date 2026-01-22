# agentic-fitness-app

## Local Fitness RAG + Trainer Agent

The system includes:

- **RAG System**: Ingesting creator markdown files, chunking + embedding locally via Ollama, persisting to ChromaDB
- **Trainer Agent**: PydanticAI-powered workout generation with "Iron Reasoning" and fatigue adaptation

### Setup

1. **Install Ollama** (for local embeddings + optional LLM):
   ```bash
   # macOS: brew install --cask ollama
   # Or download from: https://ollama.com
   
   # Pull embedding model
   ollama pull mxbai-embed-large
   
   # Pull language model (for trainer agent, if not using Gemini/OpenAI)
   ollama pull llama3.2  # Optional: only needed if using local Ollama
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Gemini API key** (recommended) or use Ollama/OpenAI:
   ```bash
   # Gemini (recommended - free tier available)
   export GOOGLE_API_KEY="your-google-api-key-here"
   # Or: export GEMINI_API_KEY="your-key-here"
   
   # Alternative: OpenAI
   export OPENAI_API_KEY="sk-your-key-here"
   
   # Alternative: Ollama (local, no API key needed)
   # Just make sure Ollama is running
   ```
   
   **Get a Gemini API key**: https://makersuite.google.com/app/apikey

### Run

#### RAG System (Ingest + Query)

- **Ingest creator data**:
  ```bash
  python main.py ingest
  ```

- **Query RAG** (filtered by creator):
  ```bash
  python main.py query --creator coach_iron --query "How should I adjust training when fatigue is high?"
  ```

#### Trainer Agent

- **Test the trainer** (generates workout from fatigue scores + philosophy):
  ```bash
  python test_trainer.py
  ```

  See `TESTING.md` for detailed testing instructions and troubleshooting.

### Project Structure

```
├── agents/
│   ├── retriever.py    # ChromaDB retrieval with creator filter
│   └── trainer.py      # PydanticAI trainer agent with Iron Reasoning
├── creators/
│   └── coach_iron.md   # Creator philosophy markdown
├── creator_db/         # ChromaDB persistence (auto-created)
├── main.py             # RAG CLI (ingest + query)
├── test_trainer.py     # Trainer agent test script
├── state.py            # FitnessState TypedDict
└── ingest.py           # RAG ingestion pipeline
```

