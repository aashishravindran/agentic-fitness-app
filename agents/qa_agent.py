"""
Q&A Agent Node

Answers conversational questions about workouts, goals, fatigue, and training
philosophy without generating a new workout plan. Integrates into the LangGraph
flow when the supervisor detects a question rather than a workout request.
"""

from __future__ import annotations

import asyncio
from typing import Dict

import config  # noqa: F401

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from agents.trainer import get_llm_model
from state import FitnessState

QA_SYSTEM_PROMPT = """You are Max, the expert fitness coach inside the SuperSet app.

Your role here is to answer the user's question concisely and helpfully — NOT to generate a workout.

You have access to the user's current state: fatigue scores, workout history, subscribed training
personas, weekly progress, and their personal goal. Use this context to give personalised,
accurate answers.

Guidelines:
- Be direct and practical. One to three short paragraphs at most.
- Reference specific numbers from the user's state when relevant (e.g. "Your legs fatigue is at 60%, so…").
- If the question is about training philosophy or a specific persona, answer from that angle.
- Never invent workouts or exercise lists — this is a Q&A interaction, not a session generator.
- If you don't know, say so honestly rather than guessing."""


class QAAnswer(BaseModel):
    answer: str = Field(description="Concise, helpful answer to the user's question")


_qa_agent: Agent | None = None


def _get_qa_agent() -> Agent:
    global _qa_agent
    if _qa_agent is None:
        _qa_agent = Agent(
            model=get_llm_model(),
            system_prompt=QA_SYSTEM_PROMPT,
            result_type=QAAnswer,
            retries=2,
        )
    return _qa_agent


def qa_worker_node(state: FitnessState) -> Dict:
    """
    Q&A node: answers the user's fitness question using their current state as context.

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

This week:
- Workouts completed: {workouts_done} / {max_workouts}

Fatigue scores (0 = fresh, 1 = exhausted, threshold = {fatigue_threshold}):
{chr(10).join(f'  - {k}: {v:.0%}' for k, v in fatigue.items()) if fatigue else '  - All fresh (no data yet)'}

Recent workout history ({len(history)} total sessions):
{recent_summary if recent_summary else '  - No sessions logged yet'}

User question: {last_user_msg}"""

    agent = _get_qa_agent()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(agent.run(context))
    answer: str = result.data.answer

    # Append answer to conversation history
    updated_messages = list(messages) + [{"role": "assistant", "content": answer}]

    return {
        "messages": updated_messages,
        "chat_response": answer,
        "daily_workout": None,   # No workout produced
        "is_working_out": False,
    }


def run_qa_standalone(user_state: dict, question: str) -> str:
    """
    Standalone helper: answer a question outside the LangGraph flow.
    Used by the CHAT_MESSAGE WebSocket handler for instant Q&A
    without touching the checkpoint / workout state.
    """
    # Reuse qa_worker_node logic by building a minimal state dict
    synthetic_state: FitnessState = {
        **user_state,  # type: ignore[misc]
        "messages": [{"role": "user", "content": question}],
    }
    result = qa_worker_node(synthetic_state)
    return result.get("chat_response", "I'm not sure — try rephrasing your question.")
