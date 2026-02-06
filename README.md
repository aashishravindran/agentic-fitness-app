# agentic-fitness-app

## Agentic Fitness Platform with AI Coaching

> 🚀 **New to the project? Start with [QUICKSTART.md](./QUICKSTART.md) for CLI setup or [QUICKSTART_UI.md](./QUICKSTART_UI.md) for UI setup!**
>
> 📖 **For comprehensive documentation, see [PROJECT_DOCUMENTATION.md](./PROJECT_DOCUMENTATION.md)**

A full-stack fitness coaching platform powered by LangGraph agents, featuring:

- **RAG System**: Ingesting creator markdown files, chunking + embedding locally via Ollama, persisting to ChromaDB
- **Multi-Agent System**: Supervisor routes to specialist workers (Iron, Yoga, HIIT, Kickboxing)
- **Real-Time UI**: React frontend with WebSocket support for live workout sessions
- **Fatigue Tracking**: Time-based decay, RPE-based accumulation, and rest day recovery
- **State Persistence**: SQLite checkpoints for per-user workout history and progress

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

## Quick Start

### Option 1: Web UI (Recommended)

**Full-stack application with modern React UI:**

1. **Install dependencies**:
   ```bash
   # Backend
   pip install -r requirements.txt
   
   # Frontend
   cd frontend && npm install && cd ..
   ```

2. **Start backend** (Terminal 1):
   ```bash
   python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Start frontend** (Terminal 2):
   ```bash
   cd frontend && npm run dev
   ```

4. **Open browser**: `http://localhost:5173`

See **[QUICKSTART_UI.md](./QUICKSTART_UI.md)** for detailed UI setup instructions.

### Option 2: CLI Interface

**Command-line interface for testing and development:**

#### RAG System (Ingest + Query)

- **Ingest creator data**:
  ```bash
  python main.py ingest
  ```

- **Query RAG** (filtered by creator):
  ```bash
  python main.py query --creator coach_iron --query "How should I adjust training when fatigue is high?"
  ```

#### Interactive Chat CLI

- **Chat with the agent** (natural language):
  ```bash
  python main.py chat "I want a strength workout, my legs are a bit sore"
  python main.py chat "Give me a yoga flow, my hips are tight"
  python main.py chat "HIIT session please" --persona hiit
  ```

- **View user state**:
  ```bash
  python main.py db view <user_id>
  python main.py db list
  ```

See **[QUICKSTART.md](./QUICKSTART.md)** for detailed CLI instructions.

## Features

### 🎯 Multi-Agent Coaching System

**Supervisor** routes to **4 specialist workers**:
- **Iron Worker**: Strength training (push/pull/legs)
- **Yoga Worker**: Mobility (spine/hips/shoulders)
- **HIIT Worker**: Cardio (cardio/cns)
- **Kickboxing Worker**: Combat fitness (coordination/speed)

### 📊 Fatigue Management

- **Time-based decay**: Fatigue reduces automatically over time (3% per hour)
- **RPE-based accumulation**: Log sets with RPE to build realistic fatigue
- **Rest day logging**: Log rest days to reduce fatigue by 30%
- **Fatigue reset**: Reset fatigue scores manually when needed

### 💪 Workout Features

- **Real-time generation**: Get workouts instantly via natural language
- **Set logging**: Log sets with weight, reps, and RPE
- **Workout history**: All workouts saved automatically
- **Weekly tracking**: Track workouts completed per week
- **Persona switching**: Switch between Iron/Yoga/HIIT/Kickboxing on the fly

### 🎨 Modern UI

- **Mobile-first design**: Responsive React UI with Tailwind CSS
- **Real-time updates**: WebSocket connection for live state sync
- **Status dashboard**: See weekly progress, fatigue scores, and coach persona
- **RPE selector**: Tactile slider with color-coded feedback
- **Nudge system**: Agent suggestions with Accept/Ignore options

### 🔒 User Management

- **Per-user state**: Each user has isolated workout history and fatigue
- **Start fresh**: Option to reset user state when logging in
- **Switch users**: Easily switch between users with proper state clearing

See **[HIERARCHICAL_SYSTEM.md](./HIERARCHICAL_SYSTEM.md)** for agent system details.

## Architecture

### Full-Stack Components

- **Backend (FastAPI)**: WebSocket server for real-time workout sessions, REST API for status/history/settings
- **Frontend (React + TypeScript)**: Modern UI with Tailwind CSS, Zustand state management, WebSocket hooks
- **Agents (LangGraph)**: Multi-agent system with Supervisor, Workers, Decay, and History Analysis nodes
- **Persistence**: SQLite checkpoints for user state, ChromaDB for RAG storage

### Project Structure

```
agentic-fitness-app/
├── backend/                # FastAPI Application
│   ├── main.py            # API entry point & WebSocket handlers
│   ├── routes/            # REST endpoints (status, history, settings)
│   └── services/          # LangGraph integration layer
├── frontend/              # React Application
│   ├── src/
│   │   ├── components/    # UI components (StatusBanner, WorkoutCard, RPESelector, etc.)
│   │   ├── hooks/         # Custom hooks (useWorkoutSocket)
│   │   └── store/         # Zustand state management
│   └── package.json
├── agents/                # LangGraph Agents
│   ├── supervisor.py      # Safety Governor & Router
│   ├── workers.py         # Specialist Workers (Iron, Yoga, HIIT, Kickboxing)
│   ├── decay.py           # Time-based fatigue decay
│   ├── history_analyzer.py # History-based fatigue analysis
│   ├── finalize_workout.py # RPE-based fatigue application
│   └── log_rest.py        # Rest day logging
├── creators/              # Creator philosophy markdown files
├── creator_db/            # ChromaDB persistence (auto-created)
├── checkpoints/          # SQLite checkpoints (auto-created)
├── graph.py              # LangGraph workflow definition
├── state.py              # Shared FitnessState TypedDict
└── main.py               # CLI interface
```

## Documentation

### Getting Started
- **[QUICKSTART.md](./QUICKSTART.md)** - CLI setup and usage guide
- **[QUICKSTART_UI.md](./QUICKSTART_UI.md)** - UI/API setup and quick start
- **[README_UI.md](./README_UI.md)** - UI architecture and API documentation

### System Architecture
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - ⭐ Complete system architecture and components
- **[PROJECT_DOCUMENTATION.md](./PROJECT_DOCUMENTATION.md)** - Comprehensive project overview
- **[HIERARCHICAL_SYSTEM.md](./HIERARCHICAL_SYSTEM.md)** - Multi-agent system implementation
- **[UI_IMPLEMENTATION_SUMMARY.md](./UI_IMPLEMENTATION_SUMMARY.md)** - UI implementation details

### Features & Fixes
- **[FEATURE_LOG_REST.md](./FEATURE_LOG_REST.md)** - Rest day logging feature
- **[FEATURE_RESET_FATIGUE.md](./FEATURE_RESET_FATIGUE.md)** - Fatigue reset feature
- **[BUG_FIX_SWITCH_USER.md](./BUG_FIX_SWITCH_USER.md)** - Switch user bug fix
- **[FIX_FATIGUE_AND_RESET_WORKOUTS.md](./FIX_FATIGUE_AND_RESET_WORKOUTS.md)** - Fatigue and workout reset fixes

### Setup & Testing
- **[TESTING.md](./TESTING.md)** - Testing guide and troubleshooting
- **[GEMINI_SETUP.md](./GEMINI_SETUP.md)** - Gemini API setup instructions
- **[FITNESS_RAG_SPEC.md](./FITNESS_RAG_SPEC.md)** - Original technical specification
- **[PITCH_DECK.md](./PITCH_DECK.md)** - 🎯 Pitch deck for non-technical audiences

## API Endpoints

### WebSocket: `/ws/workout/{user_id}`

Real-time connection for workout sessions.

**Client Messages**:
- `USER_INPUT`: `{"type": "USER_INPUT", "content": "Start leg day", "persona": "iron"}`
- `LOG_SET`: `{"type": "LOG_SET", "data": {"exercise": "Squat", "weight": 225, "reps": 5, "rpe": 9}}`
- `LOG_REST`: `{"type": "LOG_REST"}` - Log a rest day
- `FINISH_WORKOUT`: `{"type": "FINISH_WORKOUT"}`
- `RESET_FATIGUE`: `{"type": "RESET_FATIGUE"}` - Reset fatigue scores
- `RESET_WORKOUTS`: `{"type": "RESET_WORKOUTS"}` - Reset weekly counter

**Server Messages**:
- `AGENT_RESPONSE`: `{"type": "AGENT_RESPONSE", "state": {...}, "workout": {...}}`
- `ERROR`: `{"type": "ERROR", "message": "..."}`

### REST Endpoints

- `GET /api/users/{user_id}/status` - Get weekly progress and fatigue scores
- `GET /api/users/{user_id}/history` - Get workout history
- `PATCH /api/users/{user_id}/settings` - Update user settings

## Database Management

View and manage users in the database:

```bash
# List all users
python main.py db list

# View user state
python main.py db view <user_id>

# Update fatigue scores
python main.py db update-fatigue <user_id> "legs:0.5,push:0.3"

# Reset workouts counter
python main.py db new-week <user_id>

# Or use the simple script
python view_users.py
python view_users.py <user_id>  # View specific user
```

See **[VIEW_USERS.md](./VIEW_USERS.md)** for all database commands.

