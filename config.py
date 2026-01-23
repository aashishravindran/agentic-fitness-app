"""
Configuration loader with .env file support.

This module loads environment variables from .env file if it exists.
All agents and workers will automatically use these values.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    # If python-dotenv not installed, just use os.getenv
    def load_dotenv(*args, **kwargs):
        pass


def load_config():
    """Load environment variables from .env file."""
    # Look for .env in project root
    env_path = Path(__file__).parent / ".env"
    
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        # Silent load - no print to avoid noise
    else:
        # Try .env.example as fallback (for documentation)
        example_path = Path(__file__).parent / ".env.example"
        if example_path.exists():
            print(f"⚠️  No .env file found. Copy .env.example to .env and add your API keys.")
        # If no .env or .env.example, silently use system environment variables


# Auto-load on import
load_config()
