"""
Q&A Agent Node (Command Hub)

Answers conversational questions about workouts, goals, fatigue, and training
philosophy without generating a new workout plan. Also detects and executes
user commands like "reset my fatigue", "increase workouts to 5", "I just got
a barbell", etc.

Integrates into the LangGraph flow when the supervisor detects a question or
command rather than a workout request.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import config  # noqa: F401

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from agents.trainer import get_llm_model
from state import FitnessState

logger = logging.getLogger(__name__)

QA_SYSTEM_PROMPT = """You are Max, the expert fitness coach inside the SuperSet app.

Your role is to answer the user's question concisely and helpfully — NOT to generate a workout.

You have access to the user's current state: fatigue scores, workout history, subscribed training
personas, weekly progress, equipment, workout duration, and their personal goal. Use this context
to give personalised, accurate answers.

## Command Detection

You can also detect and execute user commands. If the user's message is a command (not a question),
set the appropriate command field:

- "reset my fatigue" / "clear fatigue" → command: "reset_fatigue"
- "reset workouts" / "start fresh this week" → command: "reset_workouts"
- "increase workouts to 5" / "I want to work out 6 times a week" → command: "set_max_workouts", command_args: {"value": <number>}
- "I only have 20 minutes today" / "make workouts 45 min" → command: "set_duration", command_args: {"value": <minutes>}
- "I just got a barbell" / "I only have dumbbells and bands" → command: "update_equipment", command_args: {"equipment": ["dumbbells", "resistance bands"]}
- "set fatigue threshold to 0.9" → command: "set_fatigue_threshold", command_args: {"value": <float>}

For commands, provide a friendly confirmation message in 'answer' (e.g. "Done! I've updated your equipment list.").
If it's a pure question (no state change needed), leave command as null.

## Q&A Guidelines
- Be direct and practical. One to three short paragraphs at most.
- Reference specific numbers from the user's state when relevant (e.g. "Your legs fatigue is at 60%, so…").
- If the question is about training philosophy or a specific persona, answer from that angle.
- Never invent workouts or exercise lists — this is a Q&A interaction, not a session generator.
- If you don't know, say so honestly rather than guessing."""


class CommandArgs(BaseModel):
    """Typed command arguments (Gemini-compatible — no Dict[str, Any])."""
    numeric_value: Optional[float] = Field(
        default=None,
        description="Numeric value for commands like set_max_workouts (5), set_duration (30), set_fatigue_threshold (0.9)"
    )
    equipment_list: Optional[List[str]] = Field(
        default=None,
        description="Equipment list for update_equipment command (e.g. ['barbell', 'dumbbells', 'pull-up bar'])"
    )


class QAResponse(BaseModel):
    answer: str = Field(description="Concise, helpful answer to the user's question or command confirmation")
    command: Optional[str] = Field(
        default=None,
        description="Command to execute: reset_fatigue, reset_workouts, set_max_workouts, "
        "set_duration, update_equipment, set_fatigue_threshold, or null for pure Q&A"
    )
    command_args: Optional[CommandArgs] = Field(
        default=None,
        description="Arguments for the command"
    )


_qa_agent: Agent | None = None


def _get_qa_agent() -> Agent:
    global _qa_agent
    if _qa_agent is None:
        _qa_agent = Agent(
            model=get_llm_model(),
            system_prompt=QA_SYSTEM_PROMPT,
            result_type=QAResponse,
            retries=2,
        )
    return _qa_agent


def _execute_command(user_id: str, command: str, args: Optional[CommandArgs]) -> bool:
    """Execute a detected command by updating the checkpoint state."""
    if not user_id:
        return False
    if args is None:
        args = CommandArgs()
    try:
        from db_utils import (
            get_user_state,
            _save_state_to_checkpoint,
            update_user_fatigue,
            update_workouts_completed,
            update_max_workouts,
            update_fatigue_threshold,
        )

        if command == "reset_fatigue":
            state = get_user_state(user_id)
            if state:
                zeroed = {k: 0.0 for k in state.get("fatigue_scores", {})}
                return update_user_fatigue(user_id, zeroed)
        elif command == "reset_workouts":
            return update_workouts_completed(user_id, 0)
        elif command == "set_max_workouts":
            value = int(args.numeric_value) if args.numeric_value is not None else 4
            return update_max_workouts(user_id, value)
        elif command == "set_duration":
            state = get_user_state(user_id)
            if state:
                value = int(args.numeric_value) if args.numeric_value is not None else 30
                state["workout_duration_minutes"] = value
                return _save_state_to_checkpoint(user_id, state)
        elif command == "update_equipment":
            state = get_user_state(user_id)
            if state:
                state["equipment"] = args.equipment_list or []
                return _save_state_to_checkpoint(user_id, state)
        elif command == "set_fatigue_threshold":
            value = float(args.numeric_value) if args.numeric_value is not None else 0.8
            return update_fatigue_threshold(user_id, value)
    except Exception as e:
        logger.error(f"Failed to execute command '{command}' for {user_id}: {e}")
    return False


def qa_worker_node(state: FitnessState) -> Dict:
    """
    Q&A node: answers the user's fitness question or executes a command.

    Routes → END (no workout generated, no finalize step).
    """
    messages = state.get("messages", [])
    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    # Build rich context from state
    fatigue = state.get("fatigue_scores") or {}
    workouts_done = state.get("workouts_completed_this_week", 0)
    max_workouts = state.get("max_workouts_per_week", 4)
    subscribed = state.get("subscribed_personas") or []
    selected_persona = state.get("selected_persona") or ""
    goal = state.get("goal") or "general fitness"
    history = state.get("workout_history") or []
    about_me = state.get("about_me") or ""
    fatigue_threshold = state.get("fatigue_threshold", 0.8)
    equipment = state.get("equipment") or []
    duration = state.get("workout_duration_minutes")

    # Fall back to selected_persona when subscribed_personas hasn't been set via onboarding
    active_personas = subscribed if subscribed else ([selected_persona] if selected_persona else [])

    # Summarise recent workouts (last 3)
    recent_summary = ""
    if history:
        recent = history[-3:]
        recent_summary = "\n".join(
            f"  - {w.get('date', 'unknown date')}: {w.get('persona', '?')} — "
            f"{w.get('focus', w.get('focus_area', 'general'))}"
            for w in recent
        )

    context = f"""User Profile:
- Goal: {goal}
- About me: {about_me or 'Not provided'}
- Active persona(s): {', '.join(active_personas) if active_personas else 'None set'}
- Equipment: {', '.join(equipment) if equipment else 'Not specified (assume full gym)'}
- Workout duration: {f'{duration} minutes' if duration else 'Not specified'}

This week:
- Workouts completed: {workouts_done} / {max_workouts}

Fatigue scores (0 = fresh, 1 = exhausted, threshold = {fatigue_threshold}):
{chr(10).join(f'  - {k}: {v:.0%}' for k, v in fatigue.items()) if fatigue else '  - All fresh (no data yet)'}

Recent workout history ({len(history)} total sessions):
{recent_summary if recent_summary else '  - No sessions logged yet'}

User message: {last_user_msg}"""

    agent = _get_qa_agent()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(agent.run(context))
    response: QAResponse = result.data
    answer: str = response.answer

    # Execute command if detected
    user_id = state.get("user_id", "")
    if response.command and user_id:
        success = _execute_command(user_id, response.command, response.command_args)
        if not success:
            answer += "\n(Note: I tried to update your settings but encountered an issue. Please try again.)"

    # Append answer to conversation history
    updated_messages = list(messages) + [{"role": "assistant", "content": answer}]

    return {
        "messages": updated_messages,
        "chat_response": answer,
        "daily_workout": None,   # No workout produced
        "is_working_out": False,
    }


def run_qa_standalone(user_state: dict, question: str, user_id: str = "") -> str:
    """
    Standalone helper: answer a question outside the LangGraph flow.
    Used by the CHAT_MESSAGE WebSocket handler for instant Q&A
    without touching the checkpoint / workout state.

    If a command is detected and user_id is provided, executes the command.
    """
    # Reuse qa_worker_node logic by building a minimal state dict
    synthetic_state: FitnessState = {
        **user_state,  # type: ignore[misc]
        "messages": [{"role": "user", "content": question}],
    }
    if user_id:
        synthetic_state["user_id"] = user_id

    result = qa_worker_node(synthetic_state)
    return result.get("chat_response", "I'm not sure — try rephrasing your question.")
