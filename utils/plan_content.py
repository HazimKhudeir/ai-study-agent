"""
Map generated markdown into named sections for tabs and quizzes.

Matching is tolerant of emoji / punctuation differences in H1 titles.
"""

from __future__ import annotations

import re

from utils.markdown_sections import split_markdown_by_h1


def _normalize_title(title: str) -> str:
    t = (title or "").lower()
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


def extract_plan_sections(markdown: str) -> dict[str, str]:
    """
    Split plan markdown into logical sections used by the UI.

    Keys include ``study_plan``, ``topics``, ``explanations``, ``questions``,
    ``answers``, ``mistakes``, ``tips``, ``overview``, and always ``full``.
    """
    sections = split_markdown_by_h1(markdown)
    out: dict[str, str] = {"full": (markdown or "").strip()}

    if not sections:
        return out

    for raw_title, body in sections:
        norm = _normalize_title(raw_title)
        if norm == "overview":
            out["overview"] = body
            continue
        if "study" in norm and "plan" in norm:
            out["study_plan"] = body
        elif "topic" in norm:
            out["topics"] = body
        elif "practice" in norm and "question" in norm:
            out["questions"] = body
        elif "question" in norm and "answer" not in norm:
            out.setdefault("questions", body)
        elif "answer" in norm:
            # e.g. "Answers & Explanations"
            out["answers"] = body
        elif "explanation" in norm:
            out["explanations"] = body
        elif "mistake" in norm:
            out["mistakes"] = body
        elif "tip" in norm:
            out["tips"] = body

    return out
