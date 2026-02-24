"""
Greeting Node

Generates a personalized greeting from Max using about_me and tonality.
Tonality is inferred from the last workout's RPE (hype/protective/neutral).
Used when the dashboard loads - does not affect workout generation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

import config  # noqa: F401

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from llm import get_llm_model

logger = logging.getLogger(__name__)


def _infer_tonality(workout_history: List[Dict]) -> str:
    """
    Infer tonality from last workout's logged RPE for Max's voice.
    Returns: "hype" | "protective" | "neutral"
    """
    if not workout_history:
        return "neutral"
    last = workout_history[-1]
    logs = last.get("_active_logs") or []
    if not logs:
        return "neutral"
    rpes = []
    for log in logs:
        for s in log.get("sets") or []:
            if isinstance(s, dict) and "rpe" in s:
                rpes.append(s["rpe"])
    if not rpes:
        return "neutral"
    avg = sum(rpes) / len(rpes)
    high_count = sum(1 for r in rpes if r >= 9)
    if high_count >= len(rpes) * 0.5:
        return "protective"
    if avg <= 6 and len(rpes) >= 3:
        return "hype"
    return "neutral"


def _user_display_name(user_id: str) -> str:
    """Extract a friendly name from user_id (e.g. aashish_ravindran_final -> Aashish)."""
    if not user_id:
        return "there"
    part = user_id.split("_")[0] if "_" in user_id else user_id
    return part.capitalize() if part else "there"


class GreetingOutput(BaseModel):
    """Greeting message from Max."""
    greeting: str = Field(description="A brief, personalized greeting (1-2 sentences)")


GREETING_PROMPT = """You are Max, a friendly AI fitness buddy for SuperSet.

Generate a brief, warm greeting for the user. Use their name if provided.
Include a nod to their about_me context if given (job, goals, trip plans, injuries).
Match the tonality: hype (celebratory), protective (empathetic, recovery-focused), or neutral.
Keep it 1-2 sentences. Be concise and encouraging."""


def _get_greeting_agent() -> Agent:
    return Agent(
        model=get_llm_model(),
        system_prompt=GREETING_PROMPT,
        result_type=GreetingOutput,
        retries=2,
    )


def _template_greeting(user_id: str, about_me: str, tonality: str) -> str:
    """Template-based greeting when ENABLE_GREETING_LLM is False."""
    name = _user_display_name(user_id)
    if about_me:
        return f"Hey {name}! Ready to optimize your stack? I've got your back."
    return f"Hey {name}! Ready to train? Let's go."


async def generate_greeting_async(
    user_id: str,
    about_me: str = "",
    workout_history: Optional[List[Dict]] = None,
) -> str:
    """
    Generate a personalized greeting from Max.
    Used when dashboard loads - does not affect workout generation.
    When ENABLE_GREETING_LLM is False, uses template (no LLM call).
    """
    from feature_flags import ENABLE_GREETING_LLM

    name = _user_display_name(user_id)
    tonality = _infer_tonality(workout_history or [])

    if not ENABLE_GREETING_LLM:
        return _template_greeting(user_id, about_me, tonality)

    context = f"User's name or identifier: {name}. Tonality: {tonality}."
    if about_me:
        context += f" About them: {about_me}."
    context += " Generate a greeting."
    try:
        agent = _get_greeting_agent()
        result = await agent.run(context)
        return result.data.greeting.strip()
    except Exception as e:
        logger.warning(f"Greeting LLM failed: {e}. Using fallback.")
        return _template_greeting(user_id, about_me, tonality)


def generate_greeting(
    user_id: str,
    about_me: str = "",
    workout_history: Optional[List[Dict]] = None,
) -> str:
    """Synchronous wrapper for generate_greeting_async."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(
        generate_greeting_async(user_id, about_me, workout_history)
    )


async def generate_greeting_for_dashboard(
    user_id: str,
    about_me: str = "",
    workout_history: Optional[List[Dict]] = None,
) -> str:
    """Async version for backend WebSocket handler."""
    return await generate_greeting_async(user_id, about_me, workout_history)
