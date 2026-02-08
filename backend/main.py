"""
FastAPI Application Entry Point

Handles WebSocket connections for real-time workout sessions and REST API endpoints.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import sys
from pathlib import Path

# Add backend directory to path for imports
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from routes import history, onboard, settings, status, workout
from services.workout_service import WorkoutService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store active WebSocket connections per user
active_connections: Dict[str, WebSocket] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown tasks."""
    logger.info("Starting FastAPI application...")
    yield
    logger.info("Shutting down FastAPI application...")


# Create FastAPI app
app = FastAPI(
    title="Agentic Fitness App API",
    description="Backend API for the Agentic Fitness App with WebSocket support",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite and Next.js defaults
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API routes
app.include_router(status.router, prefix="/api", tags=["status"])
app.include_router(history.router, prefix="/api", tags=["history"])
app.include_router(settings.router, prefix="/api", tags=["settings"])
app.include_router(onboard.router, prefix="/api", tags=["onboard"])
app.include_router(workout.router, prefix="/api", tags=["workout"])


@app.websocket("/ws/workout/{user_id}")
async def workout_websocket(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time workout sessions.
    
    Protocol:
    - Client sends: {"type": "USER_INPUT", "content": "Start leg day"}
    - Client sends: {"type": "LOG_SET", "data": {"exercise": "Squat", "weight": 225, "reps": 5, "rpe": 9}}
    - Client sends: {"type": "APPROVE_SUGGESTION", "approved": true}
    - Server sends: {"type": "AGENT_RESPONSE", "state": {...}, "workout": {...}}
    """
    await websocket.accept()
    active_connections[user_id] = websocket
    logger.info(f"WebSocket connected for user: {user_id}")
    
    # Initialize workout service for this user
    workout_service = WorkoutService(user_id=user_id)
    
    try:
        # Check if client wants to start fresh (via query param or initial message)
        # For now, we'll handle it via a RESET_USER message
        
        # Send initial state if available (but only if it exists and has meaningful data)
        initial_state = await workout_service.get_current_state()
        if initial_state and (initial_state.get("daily_workout") or initial_state.get("workout_history")):
            await websocket.send_json({
                "type": "AGENT_RESPONSE",
                "state": initial_state,
                "workout": initial_state.get("daily_workout"),
            })
        else:
            # Send empty state to ensure frontend knows there's no data
            await websocket.send_json({
                "type": "AGENT_RESPONSE",
                "state": None,
                "workout": None,
            })
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            logger.info(f"Received message type '{message_type}' from user {user_id}")
            
            if message_type == "USER_INPUT":
                # Handle natural language input or command
                content = data.get("content", "")
                persona = data.get("persona", "iron")  # Default persona
                goal = data.get("goal", "Build strength and improve fitness")
                max_workouts_per_week = data.get("max_workouts_per_week")  # Optional; used for new users

                try:
                    # Run the workout graph
                    logger.info(f"Processing user input for {user_id}: {content[:50]}...")
                    result = await workout_service.process_user_input(
                        content=content,
                        persona=persona,
                        goal=goal,
                        max_workouts_per_week=max_workouts_per_week,
                    )
                    
                    logger.info(f"Workout generated for {user_id}. Daily workout: {result.get('daily_workout') is not None}")
                    
                    # Send response back
                    await websocket.send_json({
                        "type": "AGENT_RESPONSE",
                        "state": result,
                        "workout": result.get("daily_workout"),
                        "is_working_out": result.get("is_working_out", False),
                    })
                    
                    # If graph is interrupted (waiting for user action), wait for resume
                    if result.get("is_working_out"):
                        logger.info(f"Graph interrupted for user {user_id}, waiting for resume...")
                        # The graph will resume when user sends LOG_SET or APPROVE_SUGGESTION
                except Exception as e:
                    logger.error(f"Error processing user input for {user_id}: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "ERROR",
                        "message": f"Failed to generate workout: {str(e)}",
                    })
                    
            elif message_type == "LOG_SET":
                # Handle set logging
                set_data = data.get("data", {})
                exercise_name = set_data.get("exercise")
                exercise_id = set_data.get("exercise_id")
                weight = set_data.get("weight", 0.0)
                reps = set_data.get("reps", 0)
                rpe = set_data.get("rpe", 5)
                
                result = await workout_service.log_set(
                    exercise_name=exercise_name,
                    exercise_id=exercise_id,
                    weight=weight,
                    reps=reps,
                    rpe=rpe,
                )
                
                await websocket.send_json({
                    "type": "AGENT_RESPONSE",
                    "state": result,
                    "workout": result.get("daily_workout"),
                })
                
            elif message_type == "APPROVE_SUGGESTION":
                # Handle approval/rejection of agent suggestions
                approved = data.get("approved", False)
                
                result = await workout_service.approve_suggestion(approved=approved)
                
                await websocket.send_json({
                    "type": "AGENT_RESPONSE",
                    "state": result,
                    "workout": result.get("daily_workout"),
                })
                
            elif message_type == "RESUME":
                # Resume the graph after interruption
                result = await workout_service.resume_graph()
                
                await websocket.send_json({
                    "type": "AGENT_RESPONSE",
                    "state": result,
                    "workout": result.get("daily_workout"),
                    "is_working_out": result.get("is_working_out", False),
                })
                
            elif message_type == "FINISH_WORKOUT":
                # Finish the current workout session
                result = await workout_service.finish_workout()
                
                # Clear workout from frontend after completion
                await websocket.send_json({
                    "type": "AGENT_RESPONSE",
                    "state": result,
                    "workout": None,  # Explicitly set to None
                    "workout_completed": True,
                    "is_working_out": False,
                })
                
            elif message_type == "RESET_USER":
                # Reset user state to start fresh
                logger.info(f"Resetting user state for {user_id}")
                success = await workout_service.reset_user_state()
                
                if success:
                    await websocket.send_json({
                        "type": "AGENT_RESPONSE",
                        "state": None,
                        "workout": None,
                        "user_reset": True,
                    })
                else:
                    await websocket.send_json({
                        "type": "ERROR",
                        "message": "Failed to reset user state",
                    })
                
            elif message_type == "RESET_FATIGUE":
                # Reset fatigue scores to defaults
                logger.info(f"Resetting fatigue scores for {user_id}")
                result = await workout_service.reset_fatigue_scores()
                
                await websocket.send_json({
                    "type": "AGENT_RESPONSE",
                    "state": result,
                    "workout": result.get("daily_workout"),
                })
                
            elif message_type == "RESET_WORKOUTS":
                # Reset workouts completed counter to zero
                logger.info(f"Resetting workouts completed counter for {user_id}")
                result = await workout_service.reset_workouts_completed()
                
                await websocket.send_json({
                    "type": "AGENT_RESPONSE",
                    "state": result,
                    "workout": result.get("daily_workout"),
                })
                
            elif message_type == "LOG_REST":
                # Log a rest day and reduce fatigue scores
                logger.info(f"Logging rest day for {user_id}")
                result = await workout_service.log_rest_day()
                
                await websocket.send_json({
                    "type": "AGENT_RESPONSE",
                    "state": result,
                    "workout": result.get("daily_workout"),
                    "rest_logged": True,
                })
                
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await websocket.send_json({
                    "type": "ERROR",
                    "message": f"Unknown message type: {message_type}",
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user: {user_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket handler for user {user_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "ERROR",
                "message": str(e),
            })
        except:
            pass
    finally:
        # Clean up connection
        active_connections.pop(user_id, None)
        logger.info(f"Cleaned up connection for user: {user_id}")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Agentic Fitness App API"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
