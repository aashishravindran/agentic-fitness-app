# Quick Start Guide

## Step-by-Step Setup

### Step 1: Prerequisites

**Install Ollama** (for embeddings):
```bash
# macOS
brew install --cask ollama

# Or download from: https://ollama.com
```

**Pull the embedding model**:
```bash
ollama pull mxbai-embed-large
```

**Verify Python** (3.10+):
```bash
python --version  # Should be 3.10 or higher
```

### Step 2: Install Dependencies

```bash
# Navigate to project directory
cd agentic-fitness-app

# Create virtual environment (recommended)
python -m venv .venv

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt
```

### Step 3: Configure API Keys

**Option A: Use .env file (Recommended)**

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your Gemini API key
# Open .env in your editor and replace:
# GOOGLE_API_KEY=your-actual-api-key-here
```

**Get a Gemini API key**: https://makersuite.google.com/app/apikey

**Option B: Environment variables**

```bash
export GOOGLE_API_KEY="your-api-key-here"
```

**Option C: Use OpenAI instead**

```bash
# In .env file:
OPENAI_API_KEY=sk-your-key-here
```

**Option D: Use Ollama (local, no API key)**

```bash
# Make sure Ollama is running
ollama serve

# Pull a language model
ollama pull llama3.2
```

### Step 4: Ingest Creator Data

This populates ChromaDB with all creator philosophies:

```bash
python main.py ingest
```

**Expected output**:
```
Ingested X chunks into collection 'creator_rules'.
```

This indexes all 4 creators:
- `coach_iron.md` (Strength training)
- `zenflow_yoga.md` (Yoga/mobility)
- `inferno_hiit.md` (HIIT/cardio)
- `strikeforce_kb.md` (Kickboxing)

### Step 5: Test the System

**Option A: Test Single Trainer Agent**

```bash
python test_trainer.py
```

**Option B: Test Full Multi-Agent System**

```bash
python test_graph.py
```

This tests all 4 workers (Iron, Yoga, HIIT, Kickboxing).

**Option C: Chat CLI (natural language → Supervisor → agents)**

```bash
# Natural language query — Supervisor routes to the right agent
python main.py chat "I want a strength workout, my legs are a bit sore"
python main.py chat "Give me a yoga flow, my hips are tight"
python main.py chat "HIIT session please" --persona hiit
```

**Option D: Other CLI Commands**

```bash
# Query RAG system
python main.py query --creator coach_iron --query "How should I adjust training when fatigue is high?"

# Generate workout directly (single trainer)
python main.py train --creator coach_iron --goal "Build strength" --fatigue "legs:0.3,push:0.2,pull:0.1"
```

## Common Commands

### Chat CLI (Supervisor + Agents)

```bash
# Natural language → Supervisor routes → Worker generates workout
python main.py chat "I want a strength workout"
python main.py chat "Yoga session, my hips are tight"
python main.py chat "HIIT please" --persona hiit

# Optional flags
python main.py chat "Strength day" --persona iron --goal "Build muscle" --fatigue "legs:0.5"
python main.py chat "Recovery yoga" --json   # output workout as JSON
```

### RAG System

```bash
# Ingest all creators
python main.py ingest

# Query specific creator
python main.py query --creator zenflow_yoga --query "What poses help with hip tightness?"

# Query with custom parameters
python main.py query \
  --creator inferno_hiit \
  --query "How do I structure a HIIT session?" \
  --k 8
```

### Trainer Agent

```bash
# Basic workout generation
python main.py train

# With custom fatigue scores
python main.py train \
  --fatigue "legs:0.8,push:0.2,pull:0.3" \
  --goal "Recovery day"

# Output as JSON
python main.py train --json
```

### Multi-Agent System

```python
from graph import run_workout

# Generate workout with full system
result = run_workout(
    user_id="user_123",
    persona="yoga",  # or "iron", "hiit", "kickboxing"
    goal="Improve flexibility",
    fatigue_scores={"hips": 0.6, "spine": 0.4},
    messages=[{"role": "user", "content": "My hips are tight"}],
)

print(result["daily_workout"])
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'langchain_community'"

**Fix**: Install dependencies
```bash
pip install -r requirements.txt
```

### "No .env file found"

**Fix**: Create `.env` file
```bash
cp .env.example .env
# Then edit .env and add your API key
```

### "Connection refused" (Ollama)

**Fix**: Start Ollama
```bash
ollama serve
```

### "Model not found" (Gemini)

**Fix**: 
1. Check your API key is correct in `.env`
2. Try different model: `export GEMINI_MODEL="gemini-pro"`
3. The system will auto-try multiple models

### "No results" (RAG query)

**Fix**: Run ingestion first
```bash
python main.py ingest
```

### "Creator not found"

**Fix**: Make sure creator file exists in `creators/`:
- `coach_iron.md`
- `zenflow_yoga.md`
- `inferno_hiit.md`
- `strikeforce_kb.md`

## Project Structure

```
agentic-fitness-app/
├── .env                    # Your API keys (create from .env.example)
├── .env.example            # Template for .env
├── main.py                 # CLI interface
├── graph.py                # LangGraph workflow
├── config.py               # Loads .env automatically
├── state.py                # State definitions
├── ingest.py               # RAG ingestion
├── agents/
│   ├── retriever.py        # RAG retrieval
│   ├── trainer.py          # Original trainer (legacy)
│   ├── supervisor.py       # Routing supervisor
│   ├── decay.py            # Fatigue decay
│   └── workers.py           # 4 specialist workers
├── creators/
│   ├── coach_iron.md
│   ├── zenflow_yoga.md
│   ├── inferno_hiit.md
│   └── strikeforce_kb.md
├── creator_db/             # ChromaDB (auto-created)
├── checkpoints/            # State persistence (auto-created)
├── test_trainer.py         # Test single trainer
└── test_graph.py           # Test full system
```

## Next Steps

1. **Read Documentation**:
   - [PROJECT_DOCUMENTATION.md](./PROJECT_DOCUMENTATION.md) - Full system overview
   - [HIERARCHICAL_SYSTEM.md](./HIERARCHICAL_SYSTEM.md) - Multi-agent details
   - [GEMINI_SETUP.md](./GEMINI_SETUP.md) - Gemini-specific setup

2. **Customize Creators**: Edit markdown files in `creators/` to change philosophies

3. **Build Frontend**: Use the JSON output from workouts to build a UI

4. **Add Features**: 
   - Nutritionist agent
   - Workout history
   - User management

## Quick Test Checklist

- [ ] Ollama installed and `mxbai-embed-large` pulled
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with `GOOGLE_API_KEY`
- [ ] Ran `python main.py ingest` successfully
- [ ] Ran `python test_trainer.py` successfully
- [ ] Ran `python test_graph.py` successfully

If all checkboxes pass, you're ready to use the system! 🎉
