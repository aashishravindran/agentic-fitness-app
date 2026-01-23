# Agentic Fitness Platform - Comprehensive Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [What We've Accomplished](#what-weve-accomplished)
3. [System Architecture](#system-architecture)
4. [The Trainer Node - Deep Dive](#the-trainer-node---deep-dive)
5. [RAG System](#rag-system)
6. [State Management](#state-management)
7. [Usage Examples](#usage-examples)
8. [Technical Implementation](#technical-implementation)
9. [Next Steps](#next-steps)

---

## Project Overview

This is a **local-first, agentic fitness platform** that uses **Retrieval-Augmented Generation (RAG)** to provide personalized workout coaching grounded in specific "Creator" philosophies (like "Coach Iron"). The system intelligently adapts workouts based on user fatigue levels and historical training data.

### Core Concept

Instead of generic fitness advice, users select a "Creator" (e.g., "Coach Iron") whose training philosophy is stored in markdown files. The system:
1. Retrieves the creator's philosophy from a vector database
2. Analyzes user fatigue scores
3. Generates personalized workouts that respect both the creator's rules and the user's recovery state
4. Provides structured, JSON-friendly output for frontend integration

---

## What We've Accomplished

### ✅ Phase 1: RAG Foundation (Complete)

**1. Document Ingestion Pipeline (`ingest.py`)**
- Scans `creators/` directory for markdown files
- Chunks documents using `RecursiveCharacterTextSplitter` (900 chars, 120 overlap)
- Generates embeddings locally via Ollama (`mxbai-embed-large`)
- Stores chunks in ChromaDB with metadata: `creator_name`, `source`, `chunk` index
- Persists to local `creator_db/` directory

**2. Retrieval System (`agents/retriever.py`)**
- Semantic search with creator filtering
- Returns top-k chunks based on query similarity
- LangGraph-compatible `retrieve_node()` function
- Configurable via `RetrieverConfig`

**3. CLI Interface (`main.py`)**
- `python main.py ingest` - Populate ChromaDB
- `python main.py query` - Test RAG retrieval
- `python main.py train` - Generate workouts

### ✅ Phase 2: Trainer Agent (Complete)

**1. PydanticAI Integration (`agents/trainer.py`)**
- Structured output using Pydantic models (`Exercise`, `WorkoutPlan`)
- Multi-LLM support: Gemini (default), OpenAI, Ollama
- Automatic model fallback if primary model fails
- "Iron Reasoning" system prompt for consistent coaching style

**2. Fatigue-Aware Workout Generation**
- Analyzes `fatigue_scores` from state
- Automatically adapts when fatigue > 0.6
- Pivots to recovery-aligned movements or different muscle groups
- Provides justification for each exercise based on creator's philosophy

**3. State Management (`state.py`)**
- `FitnessState` TypedDict with all required fields
- Tracks: user_id, creator, goal, fatigue_scores, retrieved_rules, workouts
- JSON-friendly structure for frontend integration

### ✅ Phase 3: Testing & Documentation

- Test scripts (`test_trainer.py`)
- Example code (`examples/call_trainer_directly.py`)
- Comprehensive setup guides (`TESTING.md`, `GEMINI_SETUP.md`)
- Project documentation (this file)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User/CLI Interface                        │
│  (main.py: ingest, query, train commands)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAG System Layer                          │
│                                                              │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │  ingest.py   │─────▶│  ChromaDB     │                   │
│  │  (Chunking + │      │  (Vector DB)  │                   │
│  │  Embedding)  │      │               │                   │
│  └──────────────┘      └───────┬───────┘                   │
│                                 │                            │
│                       ┌─────────▼─────────┐                 │
│                       │  retriever.py     │                 │
│                       │  (Semantic Search)│                 │
│                       └─────────┬─────────┘                 │
└─────────────────────────────────┼───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  Trainer Agent Layer                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  trainer_node(state: FitnessState)                  │  │
│  │                                                       │  │
│  │  1. Fetch Philosophy (from RAG or cache)            │  │
│  │  2. Build Context Prompt                            │  │
│  │     - Fatigue scores                                │  │
│  │     - Creator rules                                 │  │
│  │     - User goal                                      │  │
│  │  3. Generate Structured Workout (PydanticAI)        │  │
│  │  4. Return updated state                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  PydanticAI Agent                                     │  │
│  │  - System Prompt: "Iron Reasoning"                   │  │
│  │  - Result Type: WorkoutPlan (structured)             │  │
│  │  - LLM: Gemini/OpenAI/Ollama (configurable)          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    State & Output                            │
│                                                              │
│  FitnessState:                                              │
│  - daily_workout: Dict (JSON-friendly)                     │
│  - retrieved_philosophy: str                                │
│  - current_workout: str (legacy)                           │
└─────────────────────────────────────────────────────────────┘
```

---

## The Trainer Node - Deep Dive

### Overview

The **Trainer Node** (`trainer_node()`) is the core intelligence of the system. It takes user state (fatigue, goals, creator selection) and generates personalized workout plans that respect both the creator's philosophy and the user's recovery needs.

### Function Signature

```python
async def trainer_node(state: FitnessState) -> Dict
```

**Input:** `FitnessState` dictionary with:
- `user_id`: User identifier
- `selected_creator`: Creator name (e.g., "coach_iron")
- `goal`: User's fitness goal
- `fatigue_scores`: Dict mapping muscle groups to fatigue (0.0-1.0)
- `retrieved_rules`: Optional pre-retrieved chunks (can be empty)
- `retrieved_philosophy`: Optional cached philosophy (can be empty)

**Output:** Dictionary with:
- `daily_workout`: Structured workout plan (Dict, JSON-friendly)
- `retrieved_philosophy`: Combined philosophy text
- `current_workout`: JSON string (for backward compatibility)

### Step-by-Step Process

#### Step 1: Philosophy Retrieval

```python
if not state.get("retrieved_philosophy") and state.get("retrieved_rules"):
    # Use cached rules
    philosophy = "\n\n".join(state["retrieved_rules"])
elif not state.get("retrieved_philosophy"):
    # Fetch from ChromaDB
    rules = retrieve_creator_rules(
        query="Provide the complete training philosophy...",
        selected_creator=state["selected_creator"],
        k=8,  # Get more context
        config=cfg,
    )
    philosophy = "\n\n".join(rules)
else:
    # Use cached philosophy
    philosophy = state["retrieved_philosophy"]
```

**Why this matters:** The trainer needs the creator's complete philosophy to generate workouts that align with their principles. It intelligently uses cached data when available, or fetches fresh data from ChromaDB.

#### Step 2: Context Building

```python
# Format fatigue scores
fatigue_str = ", ".join([f"{k}: {v:.2f}" for k, v in state["fatigue_scores"].items()])

# Identify high-fatigue muscle groups (>0.6)
high_fatigue = [k for k, v in state["fatigue_scores"].items() if v > 0.6]

# Build warning if needed
if high_fatigue:
    fatigue_warning = f"⚠️ CRITICAL: {', '.join(high_fatigue)} are highly fatigued..."
```

**Fatigue Adaptation Logic:**
- If any muscle group has fatigue > 0.6, the system MUST adapt
- Options: Use recovery-aligned movements OR pivot to different muscle groups
- This prevents overtraining and respects recovery needs

#### Step 3: Prompt Construction

The prompt includes:
1. **Current Fatigue Scores**: All muscle groups with their fatigue levels
2. **Fatigue Warning**: Critical alert if any group > 0.6
3. **Creator Rules**: Complete philosophy from the creator
4. **User Goal**: What the user wants to achieve
5. **Constraints**: Explicit instructions to follow creator's rules and adapt to fatigue

#### Step 4: LLM Generation (PydanticAI)

```python
agent = get_trainer_agent()  # Lazy-initialized PydanticAI Agent
result = await agent.run(prompt)
workout_plan: WorkoutPlan = result.data
```

**The Agent Configuration:**
- **System Prompt**: "Iron Reasoning" - enforces creator philosophy adherence
- **Result Type**: `WorkoutPlan` (Pydantic model for structured output)
- **LLM**: Gemini (default), OpenAI, or Ollama (configurable)

**Structured Output:**
```python
class WorkoutPlan(BaseModel):
    focus_area: str
    total_exercises: int
    exercises: List[Exercise]
    fatigue_adaptations: Optional[str]
    overall_rationale: str

class Exercise(BaseModel):
    exercise_name: str
    sets: int
    reps: str
    tempo_notes: str
    iron_justification: str  # Key: References creator's rules
```

#### Step 5: State Update

```python
return {
    "daily_workout": workout_plan.model_dump(mode="json"),
    "retrieved_philosophy": philosophy,
    "current_workout": workout_plan.model_dump_json(),
}
```

### The "Iron Reasoning" System Prompt

This is the secret sauce that makes the trainer consistent:

```
You are the AI Digital Twin of Coach Iron. You are disciplined, technical, 
and prioritize longevity over "ego lifting."

## Core Principles:

1. **Philosophy First**: Every workout MUST follow the rules in the 
   retrieved_philosophy. If Iron says "3-second eccentrics," you must 
   explicitly state that in the exercise notes.

2. **Fatigue Mitigation**: Check the fatigue_scores. If a muscle group is 
   > 0.6 fatigued, you MUST:
   - Swap for a "Recovery-Aligned" movement (lower intensity, mobility-focused)
   - OR pivot to a different muscle group entirely
   - NEVER force heavy lifting when fatigue is high

3. **The "Iron Reasoning"**: For every exercise you suggest, provide a 
   one-sentence justification (iron_justification) referencing Coach Iron's rules.

4. **Adaptation Logic**: If fatigue_scores show legs are tired but Coach 
   Iron's philosophy says today is 'Leg Power Day,' use your reasoning to 
   suggest a modified lower-impact mobility session instead of skipping it.

5. **Output Format**: Always return structured JSON that a frontend can 
   easily render. Be specific with tempo notes and rep ranges.
```

**Why this works:**
- Forces the LLM to act as a specific persona (not generic assistant)
- Ensures every exercise references the creator's rules
- Makes fatigue adaptation mandatory, not optional
- Produces consistent, structured output

### Example Output

```json
{
  "focus_area": "Upper Body Push/Pull (Legs Recovery Day)",
  "total_exercises": 5,
  "fatigue_adaptations": "Legs are highly fatigued (0.8), so workout focuses on upper body with recovery-aligned lower body mobility.",
  "overall_rationale": "This workout aligns with Coach Iron's philosophy of progressive overload on big lifts while respecting recovery needs.",
  "exercises": [
    {
      "exercise_name": "Barbell Bench Press",
      "sets": 4,
      "reps": "5",
      "tempo_notes": "3-second eccentrics, controlled",
      "iron_justification": "Coach Iron emphasizes progressive overload on primary lifts, and bench press is a core movement pattern."
    },
    {
      "exercise_name": "Bent-Over Row",
      "sets": 4,
      "reps": "8-10",
      "tempo_notes": "2-second pause at contraction",
      "iron_justification": "Balances push movements and follows Iron's primary movement pattern (squat/hinge/press/row)."
    }
    // ... more exercises
  ]
}
```

---

## RAG System

### Ingestion Flow

1. **File Discovery**: Scans `creators/*.md` files
2. **Text Chunking**: Uses `RecursiveCharacterTextSplitter` (900 chars, 120 overlap)
3. **Embedding**: Generates vectors via Ollama (`mxbai-embed-large`)
4. **Storage**: Stores in ChromaDB with metadata:
   - `creator_name`: For filtering
   - `source`: Original file name
   - `chunk`: Chunk index

### Retrieval Flow

1. **Query Embedding**: Converts user query to vector
2. **Similarity Search**: Finds top-k similar chunks in ChromaDB
3. **Metadata Filtering**: Only returns chunks matching `creator_name`
4. **Context Assembly**: Combines chunks into philosophy text

### Why RAG?

- **Grounded Responses**: Workouts are based on actual creator documents, not LLM training data
- **Updatable**: Change creator philosophy by editing markdown files
- **Multi-Creator**: Support multiple creators with separate philosophies
- **Local-First**: No need to send creator data to cloud APIs

---

## State Management

### FitnessState Structure

```python
class FitnessState(TypedDict):
    user_id: str                    # User identifier
    selected_creator: str            # Creator name (e.g., "coach_iron")
    goal: str                       # User's fitness goal
    fatigue_scores: Dict[str, float] # {"legs": 0.8, "push": 0.2, ...}
    retrieved_rules: List[str]       # RAG chunks (can be empty)
    retrieved_philosophy: str       # Combined philosophy (can be empty)
    current_workout: Optional[str]    # Legacy JSON string
    daily_workout: Optional[Dict]    # Structured workout (JSON-friendly)
    is_approved: bool               # HITL approval status
```

### State Flow

```
Initial State
    ↓
[Retriever Node] → Adds retrieved_rules
    ↓
[Trainer Node] → Adds daily_workout, retrieved_philosophy
    ↓
[User Approval] → Sets is_approved = True
    ↓
[Nutritionist Node] → (Future: Adds macros)
```

---

## Usage Examples

### 1. CLI Usage

```bash
# Ingest creator data
python main.py ingest

# Generate workout
python main.py train \
  --creator coach_iron \
  --goal "Build strength and muscle mass" \
  --fatigue "legs:0.8,push:0.2,pull:0.3" \
  --json
```

### 2. Python Code (Async)

```python
import asyncio
from agents.trainer import trainer_node
from state import FitnessState

state: FitnessState = {
    "user_id": "user_123",
    "selected_creator": "coach_iron",
    "goal": "Build strength",
    "fatigue_scores": {"legs": 0.8, "push": 0.2},
    "retrieved_rules": [],
    "retrieved_philosophy": "",
    "current_workout": None,
    "daily_workout": None,
    "is_approved": False,
}

updated_state = await trainer_node(state)
workout = updated_state["daily_workout"]
print(f"Focus: {workout['focus_area']}")
```

### 3. Python Code (Sync)

```python
from agents.trainer import trainer_node_sync

updated_state = trainer_node_sync(state)
```

---

## Technical Implementation

### Dependencies

- **chromadb**: Vector database for RAG
- **langchain-community**: Ollama embeddings, ChromaDB integration
- **langchain-text-splitters**: Document chunking
- **pydantic-ai**: Structured LLM outputs
- **google-generativeai**: Gemini API support (optional)

### LLM Model Priority

1. **Gemini** (if `GOOGLE_API_KEY` set) - Default, free tier available
2. **OpenAI** (if `OPENAI_API_KEY` set) - Fallback option
3. **Ollama** (local) - No API key needed, runs locally

### Model Fallback Logic

If Gemini model fails, automatically tries:
- `gemini-1.5-flash` (fast, widely available)
- `gemini-1.5-pro` (more capable)
- `gemini-1.0-pro` (older stable)
- `gemini-pro` (legacy)

### File Structure

```
agentic-fitness-app/
├── agents/
│   ├── retriever.py      # RAG retrieval with creator filter
│   └── trainer.py        # Trainer agent with PydanticAI
├── creators/
│   └── coach_iron.md     # Creator philosophy markdown
├── creator_db/           # ChromaDB persistence (auto-created)
├── examples/
│   └── call_trainer_directly.py  # Usage examples
├── main.py               # CLI interface
├── ingest.py             # RAG ingestion pipeline
├── state.py              # FitnessState definition
└── test_trainer.py       # Test script
```

---

## Next Steps

### Planned Features

1. **LangGraph Integration**
   - Full workflow orchestration
   - HITL breakpoints for user approval
   - State persistence with SqliteSaver

2. **Nutritionist Agent**
   - Calculate macros for generated workouts
   - Integrate with trainer output

3. **Fatigue Analysis Node**
   - Analyze historical workout logs
   - Auto-calculate fatigue scores
   - Predict recovery needs

4. **Workout History**
   - Persist workouts to SQLite
   - Track progress over time
   - Learn from user feedback

5. **Multi-Creator Support**
   - Easy switching between creators
   - Compare philosophies
   - Hybrid approaches

### Future Enhancements

- **Web Interface**: React/Next.js frontend
- **Mobile App**: React Native integration
- **Social Features**: Share workouts, compare with others
- **Analytics**: Track adherence to creator philosophies
- **Custom Creators**: User-generated training philosophies

---

## Key Achievements

✅ **Local-First Architecture**: No cloud dependencies for core functionality  
✅ **RAG-Powered**: Workouts grounded in creator documents  
✅ **Fatigue-Aware**: Intelligent adaptation to recovery needs  
✅ **Structured Output**: JSON-friendly for easy frontend integration  
✅ **Multi-LLM Support**: Gemini, OpenAI, Ollama (flexible)  
✅ **Type-Safe**: Pydantic models ensure consistent output  
✅ **Extensible**: Easy to add new creators and features  

---

## Conclusion

We've built a solid foundation for an agentic fitness platform that:
- Respects creator philosophies through RAG
- Adapts to user fatigue intelligently
- Produces structured, consistent outputs
- Works locally with optional cloud LLMs
- Is ready for LangGraph orchestration

The **Trainer Node** is the heart of the system, combining RAG retrieval, fatigue analysis, and structured LLM generation to create personalized, philosophy-grounded workout plans.

---

*Last Updated: [Current Date]*  
*Version: 1.0 (RAG + Trainer Agent Complete)*
