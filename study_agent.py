"""
Optional CLI for quick tests without Streamlit.

Usage::

    export OPENAI_API_KEY='sk-…'
    python study_agent.py
"""

from __future__ import annotations

import os

from agent import Level, StudyAgentError, generate_study_plan
from storage.memory import build_learner_context_for_prompt


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        print(
            "Set your API key first, e.g.:\n"
            "  export OPENAI_API_KEY='sk-...'\n"
        )
        raise SystemExit(1)

    goal = input("Enter your study goal: ")
    level_raw = (
        input("Level (beginner/intermediate/advanced) [beginner]: ").strip() or "beginner"
    )
    level: Level
    if level_raw in ("beginner", "intermediate", "advanced"):
        level = level_raw
    else:
        print("Invalid level; using beginner.")
        level = "beginner"
    time_avail = input("Available time [3 days]: ").strip() or "3 days"

    ctx = build_learner_context_for_prompt()

    try:
        result = generate_study_plan(
            goal,
            level,
            time_avail,
            learner_context=ctx,
        )
    except StudyAgentError as e:
        print(f"Error: {e}")
        raise SystemExit(1) from e

    print("\n===== RESULT =====\n")
    print(result)


if __name__ == "__main__":
    main()
