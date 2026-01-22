from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent

# Try importing models - handle different pydantic-ai versions
# Initialize to None first to avoid NameError
GoogleModel = None
OpenAIModel = None
OllamaModel = None

# Try importing Google/Gemini model
try:
    from pydantic_ai.models.google import GoogleModel
except ImportError:
    try:
        from pydantic_ai.models.gemini import GeminiModel as GoogleModel
    except ImportError:
        try:
            # Some versions might have it directly in models
            from pydantic_ai.models import GoogleModel
        except ImportError:
            GoogleModel = None

# Try importing OpenAI model
try:
    from pydantic_ai.models.openai import OpenAIModel
except ImportError:
    OpenAIModel = None

# Try importing Ollama model
try:
    from pydantic_ai.models.ollama import OllamaModel
except ImportError:
    # Fallback: pydantic-ai might use a different structure
    try:
        from pydantic_ai.models import OllamaModel
    except ImportError:
        OllamaModel = None

from agents.retriever import RetrieverConfig, retrieve_creator_rules
from state import FitnessState


# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================


class Exercise(BaseModel):
    """Individual exercise in a workout."""

    exercise_name: str = Field(description="Name of the exercise (e.g., 'Barbell Back Squat')")
    sets: int = Field(description="Number of sets", ge=1, le=10)
    reps: str = Field(description="Rep range (e.g., '5', '8-10', 'AMRAP')")
    tempo_notes: str = Field(
        description="Tempo and execution notes (e.g., '3-second eccentrics, 1-second pause at bottom')"
    )
    iron_justification: str = Field(
        description="One-sentence explanation referencing Coach Iron's rules for why this exercise fits"
    )


class WorkoutPlan(BaseModel):
    """Complete workout plan with exercises and rationale."""

    focus_area: str = Field(description="Primary muscle group or movement pattern for today")
    total_exercises: int = Field(description="Number of exercises in the workout", ge=1, le=8)
    exercises: List[Exercise] = Field(description="List of exercises in order")
    fatigue_adaptations: Optional[str] = Field(
        default=None,
        description="Notes on how fatigue scores influenced exercise selection",
    )
    overall_rationale: str = Field(
        description="Brief summary of how this workout aligns with Coach Iron's philosophy"
    )


# ============================================================================
# Trainer Agent Configuration
# ============================================================================

# Iron Reasoning System Prompt
IRON_REASONING_PROMPT = """You are the AI Digital Twin of Coach Iron. You are disciplined, technical, and prioritize longevity over "ego lifting."

## Core Principles:

1. **Philosophy First**: Every workout MUST follow the rules in the retrieved_philosophy. If Iron says "3-second eccentrics," you must explicitly state that in the exercise notes.

2. **Fatigue Mitigation**: Check the fatigue_scores. If a muscle group is > 0.6 fatigued, you MUST:
   - Swap for a "Recovery-Aligned" movement (lower intensity, mobility-focused)
   - OR pivot to a different muscle group entirely
   - NEVER force heavy lifting when fatigue is high

3. **The "Iron Reasoning"**: For every exercise you suggest, provide a one-sentence justification (iron_justification) referencing Coach Iron's rules.

4. **Adaptation Logic**: If fatigue_scores show legs are tired (e.g., > 0.6) but Coach Iron's philosophy says today is 'Leg Power Day,' use your reasoning to suggest a modified lower-impact mobility session or active recovery instead of skipping it entirely.

5. **Output Format**: Always return structured JSON that a frontend can easily render. Be specific with tempo notes and rep ranges."""


def get_llm_model():
    """
    Determine which LLM backend to use based on environment variables.
    Priority: Gemini (Google) > OpenAI > Ollama (local)
    """
    # Check for Gemini/Google API key (priority)
    google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    # Default to gemini-1.5-flash (most compatible with v1beta API)
    # Will auto-fallback to other models if this one fails
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # Check for OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    # Check for Ollama (local fallback)
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")

    # Priority 1: Gemini/Google
    if google_api_key and GoogleModel:
        # Try models in order of preference (v1beta API compatible)
        models_to_try = [
            gemini_model,  # User's preferred model
            "gemini-1.5-flash",  # Fast, widely available
            "gemini-1.5-pro",  # More capable
            "gemini-1.0-pro",  # Older stable version
            "gemini-pro",  # Legacy name
        ]
        
        last_error = None
        for model_name in models_to_try:
            if model_name is None:
                continue
            try:
                return GoogleModel(model_name, api_key=google_api_key)
            except Exception as e:
                last_error = e
                # Continue to next model
                continue
        
        # If all models failed, provide helpful error
        raise ValueError(
            f"None of the Gemini models are available with your API key. "
            f"Tried: {', '.join([m for m in models_to_try if m])}\n"
            f"Last error: {last_error}\n"
            f"Check available models at: https://ai.google.dev/models/gemini"
        ) from last_error
    
    # Priority 2: OpenAI
    if openai_api_key and OpenAIModel:
        return OpenAIModel("gpt-4o-mini", api_key=openai_api_key)
    
    # Priority 3: Ollama (local)
    if OllamaModel:
        return OllamaModel(ollama_model, base_url=ollama_base_url)
    
    # Fallback errors
    if GoogleModel:
        raise ValueError(
            "No API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY for Gemini, "
            "or OPENAI_API_KEY for OpenAI, or use Ollama (local)."
        )
    raise ImportError(
        "No LLM models available. Install pydantic-ai with: "
        "pip install pydantic-ai[google] or pydantic-ai[openai] or pydantic-ai[ollama]"
    )


# Trainer Agent (lazy-initialized to avoid import-time failures)
_trainer_agent: Agent | None = None


def get_trainer_agent() -> Agent:
    """Get or create the trainer agent (lazy initialization)."""
    global _trainer_agent
    if _trainer_agent is None:
        _trainer_agent = Agent(
            model=get_llm_model(),
            system_prompt=IRON_REASONING_PROMPT,
            result_type=WorkoutPlan,
        )
    return _trainer_agent


# ============================================================================
# LangGraph Node Function
# ============================================================================


async def trainer_node(state: FitnessState) -> Dict:
    """
    Trainer Agent node for LangGraph.
    
    Flow:
    1. Fetch philosophy from ChromaDB (if not already in state)
    2. Build context prompt with fatigue scores and philosophy
    3. Generate structured workout using PydanticAI
    4. Return updated state with daily_workout and retrieved_philosophy
    
    Args:
        state: FitnessState dict with user_id, selected_creator, fatigue_scores, etc.
    
    Returns:
        Dict with updated state fields: daily_workout, retrieved_philosophy
    """
    # 1. Fetch Philosophy (using retriever if not already in state)
    if not state.get("retrieved_philosophy") and state.get("retrieved_rules"):
        # Combine retrieved rules into a single philosophy string
        philosophy = "\n\n".join(state["retrieved_rules"])
    elif not state.get("retrieved_philosophy"):
        # Need to retrieve from ChromaDB
        persist_dir = Path(__file__).parents[1] / "creator_db"
        cfg = RetrieverConfig(
            persist_dir=persist_dir,
            collection_name="creator_rules",
        )
        rules = retrieve_creator_rules(
            query="Provide the complete training philosophy, rules, and programming principles.",
            selected_creator=state["selected_creator"],
            k=8,  # Get more context for full philosophy
            config=cfg,
        )
        philosophy = "\n\n".join(rules)
    else:
        philosophy = state["retrieved_philosophy"]

    # 2. Build the "Think" Prompt
    fatigue_str = ", ".join([f"{k}: {v:.2f}" for k, v in state["fatigue_scores"].items()])
    goal = state.get("goal", "General fitness and strength")
    
    # Identify high-fatigue muscle groups
    high_fatigue = [k for k, v in state["fatigue_scores"].items() if v > 0.6]
    fatigue_warning = ""
    if high_fatigue:
        fatigue_warning = f"\n\n⚠️ CRITICAL: The following muscle groups are highly fatigued (>0.6): {', '.join(high_fatigue)}. You MUST adapt the workout to avoid these areas or use recovery-aligned movements only."

    prompt = f"""Current Fatigue Scores: {fatigue_str}
{fatigue_warning}
Creator Rules (Coach Iron's Philosophy):
{philosophy}

User Goal: {goal}

Design a workout that respects these constraints. 
- If fatigue is high (>0.6) for a muscle group, pivot to a different movement or use recovery-aligned alternatives.
- Every exercise must explicitly reference Coach Iron's rules in the iron_justification field.
- Include specific tempo notes (e.g., "3-second eccentrics" if that's in the philosophy).
- Return a structured workout plan that a frontend can render as JSON."""

    # 3. Generate Structured Output using PydanticAI
    agent = get_trainer_agent()
    result = await agent.run(prompt)
    workout_plan = result.data

    # 4. Convert to JSON-friendly dict
    daily_workout = workout_plan.model_dump(mode="json")

    # Return updated state
    return {
        "daily_workout": daily_workout,
        "retrieved_philosophy": philosophy,
        "current_workout": workout_plan.model_dump_json(),  # Also keep string version for backward compat
    }


# ============================================================================
# Synchronous Wrapper (for testing without async)
# ============================================================================


def trainer_node_sync(state: FitnessState) -> Dict:
    """
    Synchronous wrapper for trainer_node. Useful for testing.
    Requires an event loop to be running.
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(trainer_node(state))
