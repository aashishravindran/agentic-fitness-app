# Testing the Trainer Agent

## Quick Start

### Step 1: Install Dependencies

```bash
# Activate your virtual environment (if using one)
source .venv/bin/activate  # or: python -m venv .venv && source .venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

### Step 2: Set Up Ollama (Local LLM)

**Option A: Use Gemini (Recommended - Google)**
```bash
# Get your API key from: https://makersuite.google.com/app/apikey
export GOOGLE_API_KEY="your-google-api-key-here"
# Or: export GEMINI_API_KEY="your-key-here"

# Optional: Set model (default: gemini-1.5-flash)
export GEMINI_MODEL="gemini-1.5-pro"  # or gemini-1.5-flash
```

**Option B: Use OpenAI (Cloud)**
```bash
# Set your API key
export OPENAI_API_KEY="sk-your-key-here"
# Or create a .env file with: OPENAI_API_KEY=sk-...
```

**Option C: Use Ollama (Local)**
```bash
# Install Ollama (if not already installed)
# macOS: brew install --cask ollama
# Or download from: https://ollama.com

# Start Ollama service
ollama serve  # Usually runs automatically after installation

# Pull a language model (for generating workouts)
ollama pull llama3.2  # or llama3, mistral, etc.
```

### Step 3: Ingest Creator Data

```bash
# This populates ChromaDB with coach_iron.md
python main.py ingest
```

Expected output:
```
Ingested X chunks into collection 'creator_rules'.
```

### Step 4: Test the Trainer Agent

```bash
python -m tests.test_trainer
```

## What the Test Does

The test script (`tests/test_trainer.py`) will:

1. **Create sample state** with:
   - High leg fatigue (0.8) - should trigger adaptation
   - Low push/pull fatigue
   - Goal: "Build strength and muscle mass"
   - Creator: "coach_iron"

2. **Run the trainer_node** which:
   - Retrieves Coach Iron's philosophy from ChromaDB
   - Analyzes fatigue scores
   - Generates a structured workout plan
   - Adapts away from high-fatigue muscle groups

3. **Display results**:
   - Focus area
   - Exercise list with sets/reps/tempo
   - Iron Reasoning for each exercise
   - Fatigue adaptations (if any)
   - JSON output for frontend

## Expected Output

```
======================================================================
Testing Trainer Agent with High Leg Fatigue
======================================================================
Fatigue Scores: {'legs': 0.8, 'push': 0.2, 'pull': 0.3, 'core': 0.1}
Goal: Build strength and muscle mass
Creator: coach_iron

Generating workout...

======================================================================
WORKOUT GENERATED
======================================================================

Focus Area: Upper Body Push/Pull (Legs Recovery Day)
Total Exercises: 5

Fatigue Adaptations: Legs are highly fatigued (0.8), so workout focuses on upper body...

Overall Rationale: This workout aligns with Coach Iron's philosophy of...

----------------------------------------------------------------------
EXERCISES:
----------------------------------------------------------------------

1. Barbell Bench Press
   Sets: 4 | Reps: 5
   Tempo: 3-second eccentrics, controlled
   Iron Reasoning: Coach Iron emphasizes progressive overload on big lifts...

2. ...
```

## Troubleshooting

### Error: "No results. Did you run ingest first?"
- **Fix**: Run `python main.py ingest` first

### Error: "Connection refused" or API errors
- **Fix**: 
  - For Gemini: Set `GOOGLE_API_KEY` or `GEMINI_API_KEY`
  - For OpenAI: Set `OPENAI_API_KEY`
  - For Ollama: Make sure Ollama is running: `ollama serve`

### Error: "Model not found" (Ollama)
- **Fix**: Pull the model: `ollama pull llama3.2`

### Error: Import errors (pydantic-ai, etc.)
- **Fix**: Install dependencies: `pip install -r requirements.txt`
- Make sure you're in the correct virtual environment

### Error: "creator_db directory not found"
- **Fix**: Run `python main.py ingest` to create the database

## Testing Different Scenarios

You can modify `tests/test_trainer.py` to test different scenarios:

```python
# Test with low fatigue (should allow heavy leg work)
"fatigue_scores": {
    "legs": 0.2,  # Low fatigue
    "push": 0.1,
    "pull": 0.1,
}

# Test with multiple high-fatigue groups
"fatigue_scores": {
    "legs": 0.8,
    "push": 0.7,  # Also high
    "pull": 0.3,
}
```

## Next Steps

Once the trainer works, you can:
1. Integrate it into a LangGraph workflow
2. Add the Nutritionist agent
3. Add SqliteSaver for workout history
4. Build the full agentic pipeline
