# Quick Start Guide - UI & API

## Prerequisites

- Python 3.8+ with pip
- Node.js 18+ with npm
- Ollama running (for embeddings) or API keys configured in `.env`

## Step 1: Install Backend Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

## Step 3: Start Backend Server

In one terminal:

```bash
# Option 1: Using the startup script
./start_backend.sh

# Option 2: Using uvicorn directly
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will start at `http://localhost:8000`

## Step 4: Start Frontend Development Server

In another terminal:

```bash
cd frontend
npm run dev
```

The frontend will start at `http://localhost:5173`

## Step 5: Open the App

Open your browser to `http://localhost:5173`

The WebSocket will automatically connect. You should see:
- Connection status indicator (green = connected)
- Status banner with coach persona and weekly progress
- Input field to send messages to the agent

## Testing the Flow

1. **Start a workout**: Type "I want a leg workout" and click Send
2. **View workout**: The workout card will appear with exercises
3. **Log sets**: Click "Log Set" on an exercise, enter weight/reps, adjust RPE slider, click "Log Set"
4. **Finish workout**: Click "Finish Workout" when done

## Troubleshooting

### Backend won't start
- Check that all Python dependencies are installed: `pip install -r requirements.txt`
- Ensure `.env` file exists (copy from `.env.example` if needed)
- Check port 8000 is not in use

### Frontend won't start
- Check Node.js version: `node --version` (should be 18+)
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Check port 5173 is not in use

### WebSocket not connecting
- Verify backend is running on port 8000
- Check browser console for errors
- Ensure CORS is configured (should be automatic)

### No workout generated
- Check backend logs for errors
- Verify Ollama is running (if using local embeddings)
- Check API keys in `.env` file

## API curl Commands

Base URL: `http://localhost:8000`. Replace `{user_id}` with your user ID (e.g. `user1`).

**Workout flow**: The graph interrupts after generating a workout (same for REST and WebSocket). Call `log-set` to log performance, then `finish-workout` to apply fatigue and save to history.

### Recommender (Onboard)
```bash
curl -X POST http://localhost:8000/api/users/{user_id}/onboard \
  -H "Content-Type: application/json" \
  -d '{"height_cm": 180, "weight_kg": 85, "goal": "Build strength and flexibility", "fitness_level": "Intermediate"}'
```

### Profile
```bash
curl http://localhost:8000/api/users/{user_id}/profile
```

### Select Personas (subscribe to multiple)
```bash
curl -X POST http://localhost:8000/api/users/{user_id}/select-persona \
  -H "Content-Type: application/json" \
  -d '{"personas": ["iron", "yoga", "hiit"]}'
```

### Status
```bash
curl http://localhost:8000/api/users/{user_id}/status
```

### History
```bash
curl http://localhost:8000/api/users/{user_id}/history
```

### Settings
```bash
curl -X PATCH http://localhost:8000/api/users/{user_id}/settings \
  -H "Content-Type: application/json" \
  -d '{"max_workouts_per_week": 4, "fatigue_threshold": 0.8}'
```

### Generate Workout (triggers graph)
Requires user to be onboarded with at least one selected persona. Uses profile's persona and goal.
```bash
curl -X POST http://localhost:8000/api/users/{srimathi}/workout \
  -H "Content-Type: application/json" \
  -d '{"prompt": "I want a leg workout"}'
```
If user not onboarded or no persona selected, returns 400 with instructions.

### Reset Fatigue
```bash
curl -X POST http://localhost:8000/api/users/{user_id}/reset-fatigue
```

### Reset Workouts
```bash
curl -X POST http://localhost:8000/api/users/{user_id}/reset-workouts
```

### New Week
```bash
curl -X POST http://localhost:8000/api/users/{user_id}/new-week
```

### Log Set
Log a set for an exercise (call after generating a workout; repeat as needed). Use `exercise_id` (e.g. `ex_0`, `ex_1`) from the workout for reliable matching, or `exercise` name.
```bash
# By exercise ID (preferred)
curl -X POST http://localhost:8000/api/users/{user_id}/log-set \
  -H "Content-Type: application/json" \
  -d '{"exercise_id": "ex_0", "weight": 100, "reps": 5, "rpe": 8}'

# By exercise name
curl -X POST http://localhost:8000/api/users/{user_id}/log-set \
  -H "Content-Type: application/json" \
  -d '{"exercise": "Barbell Squat", "weight": 100, "reps": 5, "rpe": 8}'
```

### Finish Workout
Complete the workout session (applies fatigue, saves to history).
```bash
curl -X POST http://localhost:8000/api/users/{user_id}/finish-workout
```

### Supervisor (WebSocket)
The supervisor is invoked via WebSocket when you send `USER_INPUT`. Use `websocat`:

```bash
# Install: brew install websocat (macOS) or cargo install websocat
echo '{"type":"USER_INPUT","content":"I want a leg workout","persona":"iron","goal":"Build strength"}' | websocat ws://localhost:8000/ws/workout/user1
```

Or connect interactively:
```bash
websocat ws://localhost:8000/ws/workout/user1
# Then paste: {"type":"USER_INPUT","content":"I want a leg workout","persona":"iron","goal":"Build strength"}
```

## Next Steps

- Read `README_UI.md` for detailed architecture documentation
- Check `ARCHITECTURE.md` for system design
- Review `PROJECT_DOCUMENTATION.md` for agent details
