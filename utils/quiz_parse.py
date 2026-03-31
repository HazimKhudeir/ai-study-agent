"""
Parse practice questions and model answers for the interactive quiz.

Heuristics align with ``agent/prompts.py`` (### 🟢 Easy / 🟡 Medium / 🔴 Hard bullets).
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher


def _strip_bullet(line: str) -> str | None:
    s = line.strip()
    for prefix in ("- ", "* ", "• "):
        if s.startswith(prefix):
            return s[len(prefix) :].strip()
    m = re.match(r"^\d+\.\s+", s)
    if m:
        return s[m.end() :].strip()
    return None


def parse_questions_ordered(practice_body: str) -> list[dict[str, str]]:
    """
    Return ordered question dicts: ``label``, ``difficulty``, ``text``.

    Expected order: Easy1, Easy2, Medium1, Medium2, Hard1 (5 items when possible).
    """
    text = practice_body or ""
    lines = text.splitlines()
    current: str | None = None
    collected: list[dict[str, str]] = []

    def difficulty_from_line(line: str) -> str | None:
        low = line.lower()
        if "###" in line or line.strip().startswith("#"):
            chunk = re.sub(r"^#+\s*", "", line).strip().lower()
            if "easy" in chunk or "🟢" in line:
                return "easy"
            if "medium" in chunk or "🟡" in line:
                return "medium"
            if "hard" in chunk or "🔴" in line:
                return "hard"
        return None

    easy_n, med_n, hard_n = 0, 0, 0

    for line in lines:
        d = difficulty_from_line(line)
        if d:
            current = d
            continue
        q = _strip_bullet(line)
        if not q or not current:
            continue
        if len(q) < 2:
            continue

        if current == "easy":
            easy_n += 1
            label = f"Easy {easy_n}"
        elif current == "medium":
            med_n += 1
            label = f"Medium {med_n}"
        else:
            hard_n += 1
            label = f"Hard {hard_n}"

        collected.append({"label": label, "difficulty": current, "text": q})

    return collected[:5]


def parse_answer_chunks(answers_body: str, count: int = 5) -> list[str]:
    """
    Split the answers section into up to ``count`` chunks aligned with question order.

    Tries markdown bullets, numbered items, then paragraph splits.
    """
    body = (answers_body or "").strip()
    if not body:
        return []

    bullets: list[str] = []
    for line in body.splitlines():
        s = _strip_bullet(line)
        if s and len(s) > 1:
            bullets.append(s)
    if len(bullets) >= count:
        return bullets[:count]

    numbered = re.split(r"(?m)^(?:\d+)[.)]\s+", body)
    if len(numbered) > count:
        parts = [p.strip() for p in numbered[1:] if len(p.strip()) > 2]
        if len(parts) >= count:
            return parts[:count]

    paras = [p.strip() for p in re.split(r"\n{2,}", body) if len(p.strip()) > 5]
    if len(paras) >= count:
        return paras[:count]

    return [body] if body else []


def similarity_ratio(a: str, b: str) -> float:
    a_n = re.sub(r"\s+", " ", (a or "").strip().lower())
    b_n = re.sub(r"\s+", " ", (b or "").strip().lower())
    if not a_n or not b_n:
        return 0.0
    return SequenceMatcher(None, a_n, b_n).ratio()


def grade_response_detail(user: str, expected: str) -> dict[str, str]:
    """
    Rich grading result for portfolio UI: badge, verdict code, summary, and explanation text.

    ``verdict`` is one of: ``empty``, ``correct``, ``partial``, ``incorrect``.
    """
    u = (user or "").strip()
    e = (expected or "").strip()
    ref = (e[:400] + "…") if len(e) > 400 else e if e else "_No reference parsed — see full Answers tab._"

    if not u:
        return {
            "badge": "⚪ No answer",
            "verdict": "empty",
            "summary": "Submit a response to compare against the model answer.",
            "explanation": "Write your best attempt in the text box, then tap **Check answers**.",
        }

    ratio = similarity_ratio(u, e)
    sub_ok = bool(e) and (u.lower() in e.lower() or e.lower() in u.lower())

    if ratio >= 0.88:
        return {
            "badge": "✅ Correct",
            "verdict": "correct",
            "summary": "Your answer aligns closely with the reference.",
            "explanation": f"**Reference recap:** {ref}",
        }
    if ratio >= 0.55 or sub_ok:
        return {
            "badge": "🟡 Partially correct",
            "verdict": "partial",
            "summary": "You captured part of the idea — compare wording and details below.",
            "explanation": f"**Reference:** {ref}",
        }
    return {
        "badge": "❌ Incorrect",
        "verdict": "incorrect",
        "summary": "Your answer differs from the reference; study the explanation.",
        "explanation": f"**Reference:** {ref}",
    }


def grade_response(user: str, expected: str) -> tuple[str, str]:
    """Legacy tuple API: ``(badge, summary)``."""
    d = grade_response_detail(user, expected)
    return d["badge"], d["summary"]
