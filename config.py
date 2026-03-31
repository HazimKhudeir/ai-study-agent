"""
Application configuration: model id, limits, and on-disk paths.

Centralizing these values keeps agent, storage, and UI aligned and easier to tune in production.
"""

from __future__ import annotations

from pathlib import Path

# Project root (directory containing this file).
ROOT_DIR: Path = Path(__file__).resolve().parent

# SQLite and other local artifacts (created on demand).
DATA_DIR: Path = ROOT_DIR / "data"

# OpenAI chat model used for study plans.
OPENAI_MODEL: str = "gpt-4o-mini"

# Input limits (defensive bounds for UI + API).
MAX_GOAL_CHARS: int = 8000
MAX_TIME_CHARS: int = 500
MAX_REFERENCE_CHARS: int = 200_000

# PDF extraction defaults (balance coverage vs. latency and token use).
PDF_MAX_PAGES: int = 40
PDF_MAX_CHARS: int = 48_000

# How much recent history to inject into prompts for personalization.
LEARNER_CONTEXT_MAX_PLANS: int = 6
LEARNER_CONTEXT_MAX_CHARS: int = 3500
