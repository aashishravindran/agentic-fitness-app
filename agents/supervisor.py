"""
Supervisor Node

The "Brain" of the system. Routes user requests to appropriate specialist workers
and handles persona switching and fatigue mapping.
"""

from __future__ import annotations

from typing import Dict, List, Literal

# Load .env file if it exists
import config  # noqa: F401

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from llm import get_supervisor_model
from state import FitnessState


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
# Question starters that indicate a conversational Q&A request (not a workout request)
_QA_STARTERS = (
    "how", "what", "why", "when", "who", "where", "which", "tell me",
    "explain", "can you", "could you", "should i", "is it", "are there",
    "do i", "does", "did", "will i", "would", "advice", "help me understand",
)


def is_question(user_message: str) -> bool:
    """
    Return True when the message looks like a conversational question rather
    than a workout request.  A trailing '?' is the strongest signal; common
    question-word openings are a secondary heuristic.  Explicit workout /
    complaint keywords override so "how many squats?" still starts a workout.
    """
    if not user_message or not user_message.strip():
        return False
    text = user_message.lower().strip()

    # Explicit workout or complaint language takes priority — treat as workout
    if any(kw in text for kw in COMPLAINT_KEYWORDS):
        return False
    if any(kw in text for kw in PERSONA_SWITCH_KEYWORDS):
        return False

    # A trailing '?' is a strong question signal
    if text.endswith("?"):
        return True

    # Starts with a recognised question word
    if any(text.startswith(kw) for kw in _QA_STARTERS):
        return True

    return False


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

    next_node: Literal["iron_worker", "yoga_worker", "hiit_worker", "kb_worker", "recovery_worker", "qa_worker", "end"] = Field(
        description=(
            "Which worker node to route to. Use 'qa_worker' when the user asks a question "
            "rather than requesting a workout. Use 'recovery_worker' for rest/recovery. "
            "Use 'end' to finish."
        )
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
   - "recovery_worker" → For rest days, active recovery, or when fatigue is too high (always allowed)
   - "qa_worker" → When the user asks a question about their progress, goals, fatigue, or training
     philosophy rather than requesting a workout (e.g. "how many workouts left?", "why is my fatigue high?")
   - When user has multiple subscribed personas, pick the worker that best fits the user's message.

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
            retries=3,  # Ollama/local models often need extra retries for structured output
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
    
    # Persona-to-worker mapping
    persona_to_worker = {
        "iron": "iron_worker",
        "yoga": "yoga_worker",
        "hiit": "hiit_worker",
        "kickboxing": "kb_worker",
    }

    # Restrict to workers matching subscribed_personas (if set)
    subscribed = state.get("subscribed_personas") or []
    if subscribed:
        allowed_workers = {persona_to_worker.get(p) for p in subscribed if p in persona_to_worker}
        allowed_workers.discard(None)
        if not allowed_workers:
            allowed_workers = {"iron_worker", "yoga_worker", "hiit_worker", "kb_worker"}  # Fallback
    else:
        allowed_workers = {"iron_worker", "yoga_worker", "hiit_worker", "kb_worker"}

    def _pick_from_subscribed() -> tuple:
        """Pick worker from subscribed; use current_persona if in subscribed, else first subscribed."""
        if current_persona in subscribed:
            w = persona_to_worker.get(current_persona, "iron_worker")
            if w in allowed_workers:
                return w, current_persona
        for p in subscribed:
            w = persona_to_worker.get(p)
            if w and w in allowed_workers:
                return w, p
        # Fallback
        p = subscribed[0] if subscribed else current_persona
        return persona_to_worker.get(p, "iron_worker"), p

    # If no messages, use default routing from subscribed personas
    if not messages:
        next_worker, chosen_persona = _pick_from_subscribed()
        return {
            "next_node": next_worker,
            "selected_persona": chosen_persona,
            "selected_creator": chosen_persona,
        }

    # Short-circuit: inspect last user message before calling LLM
    last_user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_message = msg.get("content", "") or ""
            break

    # Q&A short-circuit: questions go straight to qa_worker (no LLM routing call needed)
    if is_question(last_user_message):
        return {
            "next_node": "qa_worker",
            "selected_persona": current_persona,
            "selected_creator": current_persona,
            "chat_response": None,  # will be populated by qa_worker_node
        }

    # Workout short-circuit: no complaints or persona-switch → route directly to current worker
    if not needs_llm_reasoning(last_user_message):
        next_worker, chosen_persona = _pick_from_subscribed()
        return {
            "next_node": next_worker,
            "selected_persona": chosen_persona,
            "selected_creator": chosen_persona,
        }
    
    # Build prompt from conversation
    conversation = "\n".join([
        f"{msg.get('role', 'user')}: {msg.get('content', '')}"
        for msg in messages[-5:]  # Last 5 messages for context
    ])
    
    subscribed_str = ", ".join(subscribed) if subscribed else "all"
    prompt = f"""You are the Supervisor and Safety Governor, the entry point for user interactions.

Current Persona: {current_persona}
Subscribed Personas (route ONLY to these workers): {subscribed_str}
  - iron → iron_worker, yoga → yoga_worker, hiit → hiit_worker, kickboxing → kb_worker
Current Fatigue Scores: {fatigue_scores}
Fatigue Threshold: {fatigue_threshold} (if any score exceeds this, route to recovery_worker)
Workouts Completed This Week: {workouts_completed}/{max_workouts}
Recent Conversation:
{conversation}

Analyze the conversation and decide:
1. Should the persona change based on user's request? (MUST pick from subscribed: {subscribed_str})
2. Are there any fatigue complaints to map?
3. Which worker should handle this request?
   - If user explicitly asks for rest/recovery, route to recovery_worker
   - If fatigue is high but below threshold, consider recovery_worker
   - Otherwise route to ONE worker that best fits the message - MUST be from subscribed personas only

Return your routing decision. selected_persona MUST be one of: {subscribed_str}."""
    
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
    
    # Enforce subscribed_personas: LLM must only pick from subscribed
    chosen_persona = decision.selected_persona
    next_worker = decision.next_node
    if subscribed and chosen_persona not in subscribed:
        # Override to first subscribed and map to worker
        chosen_persona = subscribed[0]
        next_worker = persona_to_worker.get(chosen_persona, "iron_worker")
        if next_worker not in allowed_workers:
            next_worker = next(iter(allowed_workers), "iron_worker")

    # Update fatigue scores with mapped complaints
    updated_fatigue = {**fatigue_scores}
    for update in decision.fatigue_updates:
        updated_fatigue[update.muscle_group] = update.fatigue_value

    return {
        "next_node": next_worker,
        "selected_persona": chosen_persona,
        "selected_creator": chosen_persona,
        "fatigue_scores": updated_fatigue,
    }
