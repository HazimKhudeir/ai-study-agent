"""
OpenAI Chat Completions wrapper: validation, message assembly, and error mapping.

This module is UI-agnostic so the same logic can be used from Streamlit or a CLI.
"""

from __future__ import annotations

import os

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

import config as app_config
from agent.errors import StudyAgentError
from agent.prompts import build_system_prompt
from agent.types import Level
from utils.validation import validate_study_inputs


def create_client() -> OpenAI:
    """Instantiate the OpenAI client using OPENAI_API_KEY from the environment."""
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise StudyAgentError(
            "Missing OPENAI_API_KEY. Set it in your environment before running the app."
        )
    return OpenAI()


def build_user_message(
    goal: str,
    level: Level,
    time_available: str,
    *,
    reference_material: str | None = None,
    learner_context: str | None = None,
) -> str:
    """
    Assemble the user message: optional memory block, then the current request.

    Order matters so the model treats the latest goal as authoritative while using history
    and PDF text as supporting context.
    """
    blocks: list[str] = []

    if learner_context and learner_context.strip():
        blocks.append(
            "## Context from prior sessions\n"
            "Use this to personalize (build on progress, avoid useless repetition). "
            "If it conflicts with the current goal, follow the current goal.\n\n"
            + learner_context.strip()
        )

    blocks.append(
        "## Current request\n"
        f"User goal: {goal.strip()}\n"
        f"Declared level: {level}\n"
        f"Available time: {time_available.strip()}"
    )

    if reference_material and reference_material.strip():
        blocks.append(
            "--- Reference material (from uploaded PDF) ---\n" + reference_material.strip()
        )

    return "\n\n".join(blocks)


def generate_study_plan(
    goal: str,
    level: Level,
    time_available: str,
    *,
    reference_material: str | None = None,
    learner_context: str | None = None,
    client: OpenAI | None = None,
) -> str:
    """
    Call the chat model and return markdown study content.

    Raises:
        StudyAgentError: Invalid input, missing API key, or mapped OpenAI/PDF-related failures.
    """
    validate_study_inputs(
        goal,
        time_available,
        reference_material=reference_material,
    )

    system_prompt = build_system_prompt(level)
    user_content = build_user_message(
        goal,
        level,
        time_available,
        reference_material=reference_material,
        learner_context=learner_context,
    )
    api = client or create_client()

    try:
        response = api.chat.completions.create(
            model=app_config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
    except RateLimitError as exc:
        raise StudyAgentError(
            "OpenAI rate limit reached. Wait briefly and try again."
        ) from exc
    except APITimeoutError as exc:
        raise StudyAgentError("The request to OpenAI timed out. Please try again.") from exc
    except APIConnectionError as exc:
        raise StudyAgentError(
            "Could not reach OpenAI. Check your network connection or VPN/firewall settings."
        ) from exc
    except APIError as exc:
        code = getattr(exc, "status_code", None)
        if code == 401:
            raise StudyAgentError(
                "API key rejected (401). Verify OPENAI_API_KEY."
            ) from exc
        if code == 429:
            raise StudyAgentError(
                "Too many requests (429). Wait and retry, or check your usage limits."
            ) from exc
        msg = getattr(exc, "message", None) or str(exc)
        raise StudyAgentError(f"OpenAI API error ({code or 'unknown'}): {msg}") from exc
    except Exception as exc:
        raise StudyAgentError(
            f"Could not reach the model ({type(exc).__name__}). Check your API key, network, and try again."
        ) from exc

    if not getattr(response, "choices", None):
        raise StudyAgentError("OpenAI returned no choices. Please try again.")
    choice = response.choices[0].message
    content = choice.content
    if not content or not str(content).strip():
        raise StudyAgentError("The model returned an empty response. Try again.")
    return str(content).strip()
