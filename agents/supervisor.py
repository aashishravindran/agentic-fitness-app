"""
Supervisor Node

The "Brain" of the system. Routes user requests to appropriate specialist workers
and handles persona switching and fatigue mapping.
"""

from __future__ import annotations

import os
from typing import Dict, List, Literal

# Load .env file if it exists
import config  # noqa: F401

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from state import FitnessState

# Try importing models
GoogleModel = None
OpenAIModel = None
OllamaModel = None

try:
    from pydantic_ai.models.google import GoogleModel
except ImportError:
    try:
        from pydantic_ai.models.gemini import GeminiModel as GoogleModel
    except ImportError:
        GoogleModel = None

try:
    from pydantic_ai.models.openai import OpenAIModel
except ImportError:
    OpenAIModel = None

try:
    from pydantic_ai.models.ollama import OllamaModel
except ImportError:
    OllamaModel = None


# Keywords that indicate the user needs LLM reasoning (complaints or persona switch)
COMPLAINT_KEYWORDS = (
    "sore", "tight", "hurt", "pain", "tired", "fatigued", "exhausted", "stiff",
    "aching", "burn", "fried", "heavy", "beat up", "cramp", "strained", "injured",
    "uncomfortable", "numb", "tingling", "swollen", "can't", "cannot", "struggling",
)
PERSONA_SWITCH_KEYWORDS = (
    "yoga", "hiit", "kickboxing", "strength", "iron", "cardio", "mobility",
    "recovery", "rest day", "stretch", "boxing", "weights", "run",
    "interval", "meditation", "flow",
)


def needs_llm_reasoning(user_message: str) -> bool:
    """
    Return True if the message contains complaints or persona-switch intent,
    so the Supervisor should call the LLM. Otherwise return False and route
    directly to the current selected_persona (0 LLM calls for routing).
    """
    if not user_message or not user_message.strip():
        return False
    text = user_message.lower().strip()
    # Complaints: any mention of discomfort or limitation
    if any(kw in text for kw in COMPLAINT_KEYWORDS):
        return True
    # Persona switch: user may be asking for a different workout type
    if any(kw in text for kw in PERSONA_SWITCH_KEYWORDS):
        return True
    return False


class FatigueUpdate(BaseModel):
    """Single fatigue update (to avoid Dict for Gemini compatibility)."""
    muscle_group: str = Field(description="Muscle group name (e.g., 'legs', 'push', 'hips')")
    fatigue_value: float = Field(description="Fatigue score (0.0 to 1.0)", ge=0.0, le=1.0)


class SupervisorDecision(BaseModel):
    """Supervisor's routing decision."""
    
    next_node: Literal["iron_worker", "yoga_worker", "hiit_worker", "kb_worker", "recovery_worker", "end"] = Field(
        description="Which worker node to route to, 'recovery_worker' for rest/recovery, or 'end' to finish"
    )
    selected_persona: Literal["iron", "yoga", "hiit", "kickboxing"] = Field(
        description="The persona/user's training style preference"
    )
    fatigue_updates: List[FatigueUpdate] = Field(
        default_factory=list,
        description="Updates to fatigue scores based on user complaints (e.g., 'my shins hurt' -> [{'muscle_group': 'legs', 'fatigue_value': 0.7}])"
    )
    reasoning: str = Field(
        description="Brief explanation of routing decision, including safety overrides if applicable"
    )


def get_supervisor_model():
    """Get LLM model for supervisor (prioritizes Gemini)."""
    google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    if google_api_key and GoogleModel:
        # Try newer model names that work with v1beta API
        # Based on pydantic-ai documentation, these are the available models
        models_to_try = [
            gemini_model,  # User's preferred model (if valid)
            "gemini-flash-latest",  # Latest flash model
            "gemini-2.0-flash",  # Gemini 2.0 flash
            "gemini-2.5-flash",  # Gemini 2.5 flash
            "gemini-2.5-pro",  # Gemini 2.5 pro
            "gemini-1.5-pro",  # Fallback to 1.5 pro
            "gemini-1.0-pro",  # Older stable version
        ]
        last_error = None
        for model_name in models_to_try:
            if not model_name:
                continue
            try:
                return GoogleModel(model_name, api_key=google_api_key)
            except Exception as e:
                last_error = e
                # Continue to next model
                continue
        
        # If all models failed, provide helpful error
        error_msg = f"Failed to initialize any Gemini model. Last error: {last_error}"
        if last_error:
            error_msg += f"\nTried models: {', '.join([m for m in models_to_try if m])}"
        raise ValueError(error_msg)
    
    if openai_api_key and OpenAIModel:
        return OpenAIModel("gpt-4o-mini", api_key=openai_api_key)
    
    if OllamaModel:
        return OllamaModel(ollama_model, base_url=ollama_base_url)
    
    raise ValueError("No LLM model available. Set GOOGLE_API_KEY, OPENAI_API_KEY, or use Ollama.")


SUPERVISOR_PROMPT = """You are the Supervisor and Safety Governor of a multi-agent fitness coaching system.

Your role:
1. **Detect Persona Switching**: If the user wants to switch training styles (e.g., "I want to do yoga today"), update selected_persona.
2. **Map Fatigue Complaints**: Translate natural language complaints to fatigue scores as a list:
   - "my shins hurt" / "legs are sore" → [{"muscle_group": "legs", "fatigue_value": 0.7}]
   - "shoulders are tight" → [{"muscle_group": "shoulders", "fatigue_value": 0.6}, {"muscle_group": "spine", "fatigue_value": 0.4}]
   - "I'm exhausted" / "CNS is fried" → [{"muscle_group": "cns", "fatigue_value": 0.8}, {"muscle_group": "cardio", "fatigue_value": 0.6}]
   - "hips are tight" → [{"muscle_group": "hips", "fatigue_value": 0.7}, {"muscle_group": "spine", "fatigue_value": 0.5}]
3. **Safety Override (CRITICAL)**: 
   - If ANY fatigue score exceeds the fatigue_threshold (default 0.8), you MUST route to "recovery_worker" regardless of user request
   - This prevents overtraining and injury
   - Only yoga_worker or recovery_worker are safe when fatigue is critical
4. **Frequency Block**: 
   - If workouts_completed_this_week >= max_workouts_per_week, route to "end" with reasoning explaining the weekly limit has been reached
5. **Route to Workers**: Based on selected_persona (if safety allows):
   - "iron" → iron_worker (strength training: push/pull/legs)
   - "yoga" → yoga_worker (mobility: spine/hips/shoulders)
   - "hiit" → hiit_worker (cardio: cardio/cns)
   - "kickboxing" → kb_worker (coordination: coordination/speed)
   - "recovery_worker" → For rest days, active recovery, or when fatigue is too high

**Fatigue Mapping Between Personas:**
- Iron's "legs" fatigue → Yoga's "hips/spine" restriction
- Iron's "push" fatigue → Yoga's "shoulders" restriction
- HIIT's "cardio" fatigue → All personas should reduce intensity

**Safety First**: Always prioritize user safety over intensity. If in doubt, route to recovery_worker.

Always provide reasoning for your routing decision, especially when safety overrides occur."""


_supervisor_agent: Agent | None = None


def get_supervisor_agent() -> Agent:
    """Get or create supervisor agent."""
    global _supervisor_agent
    if _supervisor_agent is None:
        _supervisor_agent = Agent(
            model=get_supervisor_model(),
            system_prompt=SUPERVISOR_PROMPT,
            result_type=SupervisorDecision,
        )
    return _supervisor_agent


def supervisor_node(state: FitnessState) -> Dict:
    """
    Supervisor node: Entry point for user interactions with Safety Governor logic.
    
    This is the primary interface for users. It:
    1. Processes user messages and conversation
    2. Detects persona switching
    3. Maps fatigue complaints to scores
    4. Enforces safety overrides (fatigue threshold, weekly limits)
    5. Routes to appropriate workers
    
    Args:
        state: FitnessState with messages and current persona
    
    Returns:
        Updated state with next_node, selected_persona, and fatigue_updates
    """
    # Build context from messages
    messages = state.get("messages", [])
    current_persona = state.get("selected_persona", "iron")
    fatigue_scores = state.get("fatigue_scores", {})
    fatigue_threshold = state.get("fatigue_threshold", 0.8)
    max_workouts = state.get("max_workouts_per_week", 4)
    workouts_completed = state.get("workouts_completed_this_week", 0)
    
    # SAFETY OVERRIDE 1: Frequency Block
    # If user has reached weekly limit, end the session
    if workouts_completed >= max_workouts:
        return {
            "next_node": "end",
            "selected_persona": current_persona,
            "selected_creator": current_persona,
            "fatigue_scores": fatigue_scores,
        }
    
    # SAFETY OVERRIDE 2: Fatigue Threshold
    # If any fatigue score exceeds threshold, force recovery
    max_fatigue = max(fatigue_scores.values()) if fatigue_scores else 0.0
    if max_fatigue > fatigue_threshold:
        # Force route to recovery_worker regardless of user request
        return {
            "next_node": "recovery_worker",
            "selected_persona": current_persona,
            "selected_creator": current_persona,
            "fatigue_scores": fatigue_scores,
        }
    
    # Persona-to-worker mapping (used for short-circuit and when no messages)
    persona_to_worker = {
        "iron": "iron_worker",
        "yoga": "yoga_worker",
        "hiit": "hiit_worker",
        "kickboxing": "kb_worker",
    }

    # If no messages, use default routing based on persona
    if not messages:
        return {
            "next_node": persona_to_worker.get(current_persona, "iron_worker"),
            "selected_persona": current_persona,
            "selected_creator": current_persona,
        }

    # Short-circuit: if last user message has no complaints or persona-switch, route directly (0 LLM calls)
    last_user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_message = msg.get("content", "") or ""
            break
    if not needs_llm_reasoning(last_user_message):
        return {
            "next_node": persona_to_worker.get(current_persona, "iron_worker"),
            "selected_persona": current_persona,
            "selected_creator": current_persona,
        }
    
    # Build prompt from conversation
    conversation = "\n".join([
        f"{msg.get('role', 'user')}: {msg.get('content', '')}"
        for msg in messages[-5:]  # Last 5 messages for context
    ])
    
    prompt = f"""You are the Supervisor and Safety Governor, the entry point for user interactions.

Current Persona: {current_persona}
Current Fatigue Scores: {fatigue_scores}
Fatigue Threshold: {fatigue_threshold} (if any score exceeds this, route to recovery_worker)
Workouts Completed This Week: {workouts_completed}/{max_workouts}
Recent Conversation:
{conversation}

Analyze the conversation and decide:
1. Should the persona change based on user's request?
2. Are there any fatigue complaints to map (e.g., "my legs hurt" → [{{"muscle_group": "legs", "fatigue_value": 0.7}}])?
3. Which worker should handle this request?
   - If user explicitly asks for rest/recovery, route to recovery_worker
   - If fatigue is high but below threshold, consider recovery_worker
   - Otherwise route to appropriate specialist worker

SAFETY NOTE: If max fatigue > {fatigue_threshold}, you should route to recovery_worker (but this should already be handled by safety override).

Return your routing decision."""
    
    # Get decision from supervisor agent
    import asyncio
    
    agent = get_supervisor_agent()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    result = loop.run_until_complete(agent.run(prompt))
    decision: SupervisorDecision = result.data
    
    # Update fatigue scores with mapped complaints
    # Convert List[FatigueUpdate] to Dict[str, float]
    updated_fatigue = {**fatigue_scores}
    for update in decision.fatigue_updates:
        updated_fatigue[update.muscle_group] = update.fatigue_value
    
    return {
        "next_node": decision.next_node,
        "selected_persona": decision.selected_persona,
        "selected_creator": decision.selected_persona,  # Legacy compatibility
        "fatigue_scores": updated_fatigue,
    }
