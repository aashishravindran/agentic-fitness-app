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

## Next Steps

- Read `README_UI.md` for detailed architecture documentation
- Check `ARCHITECTURE.md` for system design
- Review `PROJECT_DOCUMENTATION.md` for agent details
