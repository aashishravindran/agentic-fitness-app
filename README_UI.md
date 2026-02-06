# Agentic Fitness App - UI & API Setup Guide

This guide explains how to run the full-stack application with the new UI and API layers.

## Architecture Overview

- **Backend**: FastAPI with WebSocket support for real-time workout sessions
- **Frontend**: React + TypeScript + Tailwind CSS (Vite)
- **Agents**: Existing LangGraph workflow (unchanged)

## Quick Start

### 1. Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure your `.env` file is configured (see `.env.example`)

3. Start the FastAPI server:
```bash
cd backend
python main.py
```

Or using uvicorn directly:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 2. Frontend Setup

1. Install Node.js dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

### 3. Using the Application

1. Open `http://localhost:5173` in your browser
2. The WebSocket will automatically connect to the backend
3. Select a persona (Iron, Yoga, HIIT, Kickboxing)
4. Type a request like "Start leg day" or "I want a strength workout"
5. The agent will generate a workout plan
6. Log sets using the RPE slider and form
7. Finish the workout when done

## API Endpoints

### WebSocket: `/ws/workout/{user_id}`

Real-time connection for workout sessions.

**Client Messages:**
- `USER_INPUT`: `{"type": "USER_INPUT", "content": "Start leg day", "persona": "iron"}`
- `LOG_SET`: `{"type": "LOG_SET", "data": {"exercise": "Squat", "weight": 225, "reps": 5, "rpe": 9}}`
- `APPROVE_SUGGESTION`: `{"type": "APPROVE_SUGGESTION", "approved": true}`
- `FINISH_WORKOUT`: `{"type": "FINISH_WORKOUT"}`

**Server Messages:**
- `AGENT_RESPONSE`: `{"type": "AGENT_RESPONSE", "state": {...}, "workout": {...}}`
- `ERROR`: `{"type": "ERROR", "message": "..."}`

### REST Endpoints

- `GET /api/users/{user_id}/status` - Get weekly progress and fatigue scores
- `GET /api/users/{user_id}/history` - Get workout history
- `PATCH /api/users/{user_id}/settings` - Update user settings

## Project Structure

```
agentic-fitness-app/
├── backend/                # FastAPI Application
│   ├── main.py            # API entry point & WebSocket handlers
│   ├── routes/            # REST endpoints
│   │   ├── status.py
│   │   ├── history.py
│   │   └── settings.py
│   └── services/          # LangGraph integration
│       └── workout_service.py
├── frontend/              # React Application
│   ├── src/
│   │   ├── components/    # UI components
│   │   │   ├── StatusBanner.tsx
│   │   │   ├── WorkoutCard.tsx
│   │   │   ├── RPESelector.tsx
│   │   │   └── NudgeBanner.tsx
│   │   ├── hooks/         # Custom hooks
│   │   │   └── useWorkoutSocket.ts
│   │   ├── store/         # State management
│   │   │   └── workoutStore.ts
│   │   └── App.tsx
│   └── package.json
├── agents/                # Existing LangGraph Logic (unchanged)
├── shared/                # Shared schemas
│   └── schemas.py
└── requirements.txt       # Python dependencies
```

## Features

### Status Banner
- Shows current coach persona
- Weekly progress ring (workouts completed / max workouts)
- Fatigue scores display

### Workout Card
- Displays current workout plan
- Exercise details (sets, reps, tempo)
- Set logging interface with RPE selector

### RPE Selector
- Tactile slider (1-10)
- Color-coded feedback (green/yellow/orange/red)
- Warning for high RPE (≥9)

### Nudge Banner
- Displays agent suggestions
- Accept/Ignore buttons for recommendations

## Development Notes

### WebSocket Reconnection
The frontend automatically reconnects if the WebSocket connection is lost (3-second delay).

### State Persistence
User state is persisted using SQLite checkpoints. Each `user_id` maps to a unique thread in LangGraph.

### Fatigue Decay
The decay node runs automatically on every graph execution to ensure accurate, time-adjusted fatigue scores.

## Troubleshooting

1. **WebSocket not connecting**: Check that the backend is running on port 8000
2. **CORS errors**: Ensure CORS middleware is configured correctly in `backend/main.py`
3. **State not persisting**: Verify that the `checkpoints/` directory exists and is writable
4. **Frontend build errors**: Run `npm install` again in the `frontend/` directory

## Next Steps

- Add authentication/authorization
- Implement workout history visualization
- Add fatigue heatmap visualization
- Mobile app (React Native)
- Real-time notifications for workout reminders
