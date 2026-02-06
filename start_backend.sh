#!/bin/bash
# Start the FastAPI backend server

# Ensure we're in the project root
cd "$(dirname "$0")"

# Run the backend
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
