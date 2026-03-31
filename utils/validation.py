"""
Validate study inputs before calling the model.

Messages are written for end users (Streamlit / CLI), not developers.
"""

from __future__ import annotations

import config as app_config
from agent.errors import StudyAgentError


def validate_study_inputs(
    goal: str,
    time_available: str,
    *,
    reference_material: str | None = None,
) -> None:
    """
    Ensure goal and time are non-empty within limits; bound reference size.

    Raises:
        StudyAgentError: With a clear, actionable message for each failure mode.
    """
    goal_clean = (goal or "").strip()
    if not goal_clean:
        raise StudyAgentError("Please enter a study goal before generating a plan.")
    if len(goal_clean) > app_config.MAX_GOAL_CHARS:
        raise StudyAgentError(
            f"Study goal is too long (max {app_config.MAX_GOAL_CHARS} characters)."
        )

    time_clean = (time_available or "").strip()
    if not time_clean:
        raise StudyAgentError(
            "Please describe how much time you have (e.g. “2 weeks, 1 hour per day”)."
        )
    if len(time_clean) > app_config.MAX_TIME_CHARS:
        raise StudyAgentError(
            f"Available time text is too long (max {app_config.MAX_TIME_CHARS} characters)."
        )

    if reference_material is not None and len(reference_material) > app_config.MAX_REFERENCE_CHARS:
        raise StudyAgentError(
            "Extracted PDF text is too large to send. Try a shorter document or fewer pages."
        )
