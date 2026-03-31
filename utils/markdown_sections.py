"""
Split markdown on top-level `#` headings for card-style UI rendering.

The model emits emoji sections such as ``# 🚀 STUDY PLAN``, ``# 📚 TOPICS BREAKDOWN``, etc.
"""

from __future__ import annotations

import html
import re


def split_markdown_by_h1(markdown: str) -> list[tuple[str, str]]:
    """
    Split markdown into (title, body) pairs for each `# Heading` (not `##`).

    Preserves any preamble before the first H1 as an \"Overview\" section.
    If there are no H1 headings, returns a single section (\"Study plan\", full text).
    """
    text = (markdown or "").strip()
    if not text:
        return []

    pattern = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    if not matches:
        return [("Study plan", text)]

    out: list[tuple[str, str]] = []
    first_start = matches[0].start()
    if first_start > 0:
        preamble = text[:first_start].strip()
        if preamble:
            out.append(("Overview", preamble))

    for i, m in enumerate(matches):
        title = (m.group(1) or "Section").strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        out.append((title, body if body else "(No content under this heading.)"))

    return out


def section_card_open_html(title: str) -> str:
    """Opening markup for a section card title bar (body follows via ``st.markdown``)."""
    safe = html.escape(title)
    return f'<div class="section-card"><p class="section-card-title">{safe}</p>'
