# agentic-fitness-app

## Local Fitness RAG + Trainer Agent

> 🚀 **New to the project? Start with [QUICKSTART.md](./QUICKSTART.md) for step-by-step setup!**
>
> 📖 **For comprehensive documentation, see [PROJECT_DOCUMENTATION.md](./PROJECT_DOCUMENTATION.md)**

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
   
   **Option A: Use .env file (Recommended)**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your API key
   # GOOGLE_API_KEY=your-google-api-key-here
   ```
   
   **Option B: Environment variables**
   ```bash
   export GOOGLE_API_KEY="your-google-api-key-here"
   # Or: export GEMINI_API_KEY="your-key-here"
   ```
   
   **Alternative: OpenAI**
   ```bash
   export OPENAI_API_KEY="sk-your-key-here"
   ```
   
   **Alternative: Ollama (local, no API key needed)**
   ```bash
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

## Hierarchical Multi-Agent System

The system now includes a **Supervisor** that routes to **4 specialist workers**:

- **Iron Worker**: Strength training (push/pull/legs)
- **Yoga Worker**: Mobility (spine/hips/shoulders)
- **HIIT Worker**: Cardio (cardio/cns)
- **Kickboxing Worker**: Combat fitness (coordination/speed)

**Features**:
- Fatigue decay based on time since last session
- Automatic persona switching
- Fatigue complaint mapping
- Persistent state with SqliteSaver

**Chat CLI** (natural language → Supervisor → agents → workout):
```bash
python main.py chat "I want a strength workout, my legs are a bit sore"
python main.py chat "Give me a yoga flow, my hips are tight"
python main.py chat "HIIT session please" --persona hiit
```
Optional: `--persona`, `--goal`, `--fatigue`, `--json`.

**How to call the Supervisor**:
- **Directly** (routing + fatigue only): `from agents.supervisor import supervisor_node` → `supervisor_node(state)`
- **Full workflow** (Supervisor → Decay → Worker → workout): `from graph import run_workout` → `run_workout(...)`

**Example**: `python examples/call_supervisor.py`

**Test the full system**:
```bash
python test_graph.py
```

See **[HIERARCHICAL_SYSTEM.md](./HIERARCHICAL_SYSTEM.md)** for details.

## Documentation

- **[PITCH_DECK.md](./PITCH_DECK.md)** - 🎯 **Pitch deck for non-technical audiences - features, benefits, and roadmap**
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - ⭐ **Complete system architecture, components, and usage guide**
- **[PROJECT_DOCUMENTATION.md](./PROJECT_DOCUMENTATION.md)** - Comprehensive project overview and trainer node deep dive
- **[HIERARCHICAL_SYSTEM.md](./HIERARCHICAL_SYSTEM.md)** - Multi-agent system implementation guide
- **[QUICKSTART.md](./QUICKSTART.md)** - Step-by-step setup and quick start guide
- **[TESTING.md](./TESTING.md)** - Testing guide and troubleshooting
- **[GEMINI_SETUP.md](./GEMINI_SETUP.md)** - Gemini API setup instructions
- **[FITNESS_RAG_SPEC.md](./FITNESS_RAG_SPEC.md)** - Original technical specification

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

