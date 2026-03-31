"""
SQLite persistence: study plans, per-plan milestones, and summarized history for the model.

The database file lives under ``config.DATA_DIR`` so backups and deployments are predictable.
"""

from __future__ import annotations

import re
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any

import config as app_config

_lock = threading.Lock()


def _db_path() -> str:
    app_config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return str(app_config.DATA_DIR / "study_agent.db")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT NOT NULL,
            level TEXT NOT NULL,
            time_available TEXT NOT NULL,
            pdf_filename TEXT,
            result_markdown TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
            label TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            UNIQUE(plan_id, label)
        );
        CREATE INDEX IF NOT EXISTS idx_milestones_plan ON milestones(plan_id);
        CREATE INDEX IF NOT EXISTS idx_plans_created ON plans(created_at DESC);
        """
    )
    conn.commit()


def save_plan(
    goal: str,
    level: str,
    time_available: str,
    result_markdown: str,
    pdf_filename: str | None = None,
) -> int:
    """Persist a generated plan; returns the new row id."""
    with _lock:
        conn = get_connection()
        try:
            init_schema(conn)
            cur = conn.execute(
                """
                INSERT INTO plans (goal, level, time_available, pdf_filename, result_markdown, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    goal.strip(),
                    level,
                    time_available.strip(),
                    pdf_filename,
                    result_markdown,
                    _utc_now(),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()


def list_plans(limit: int = 25) -> list[dict[str, Any]]:
    with _lock:
        conn = get_connection()
        try:
            init_schema(conn)
            rows = conn.execute(
                """
                SELECT id, goal, level, time_available, pdf_filename, created_at,
                       LENGTH(result_markdown) AS result_len
                FROM plans
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def get_plan(plan_id: int) -> dict[str, Any] | None:
    with _lock:
        conn = get_connection()
        try:
            init_schema(conn)
            row = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def list_milestones(plan_id: int) -> list[dict[str, Any]]:
    with _lock:
        conn = get_connection()
        try:
            init_schema(conn)
            rows = conn.execute(
                """
                SELECT id, plan_id, label, done, sort_order, created_at
                FROM milestones
                WHERE plan_id = ?
                ORDER BY sort_order ASC, id ASC
                """,
                (plan_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def add_milestone(plan_id: int, label: str) -> int | None:
    label = (label or "").strip()
    if not label or len(label) > 500:
        return None
    with _lock:
        conn = get_connection()
        try:
            init_schema(conn)
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO milestones (plan_id, label, done, sort_order, created_at)
                VALUES (?, ?, 0, (SELECT COALESCE(MAX(sort_order),0)+1 FROM milestones WHERE plan_id = ?), ?)
                """,
                (plan_id, label, plan_id, _utc_now()),
            )
            conn.commit()
            if cur.rowcount:
                return int(cur.lastrowid)
            return None
        finally:
            conn.close()


def set_milestone_done(milestone_id: int, done: bool) -> None:
    with _lock:
        conn = get_connection()
        try:
            init_schema(conn)
            conn.execute(
                "UPDATE milestones SET done = ? WHERE id = ?",
                (1 if done else 0, milestone_id),
            )
            conn.commit()
        finally:
            conn.close()


def delete_milestone(milestone_id: int) -> None:
    with _lock:
        conn = get_connection()
        try:
            init_schema(conn)
            conn.execute("DELETE FROM milestones WHERE id = ?", (milestone_id,))
            conn.commit()
        finally:
            conn.close()


def suggest_milestones_from_markdown(md: str, max_items: int = 20) -> list[str]:
    """Heuristic: list-like lines under topics section (new emoji header or legacy ``# Topics``)."""
    if not md:
        return []
    patterns = (
        r"(?is)^#\s*📚\s*TOPICS\s*BREAKDOWN\s*\n(?P<body>.*?)(?=^#\s|\Z)",
        r"(?is)^#\s*Topics\s*\n(?P<body>.*?)(?=^#\s|\Z)",
    )
    m = None
    for pat in patterns:
        m = re.search(pat, md, re.MULTILINE | re.DOTALL)
        if m:
            break
    if not m:
        return []
    body = m.group("body")
    seen: set[str] = set()
    out: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        text: str | None = None
        if line.startswith(("- ", "* ")):
            text = line[2:].strip()
        elif line.startswith("• "):
            text = line[2:].strip()
        elif re.match(r"^\d+\.\s+", line):
            text = re.sub(r"^\d+\.\s+", "", line).strip()
        elif line.startswith("## "):
            text = line[3:].strip()
        if text and len(text) < 400 and text not in seen:
            seen.add(text)
            out.append(text)
        if len(out) >= max_items:
            break
    return out


def import_suggested_milestones(plan_id: int, md: str) -> int:
    """Insert suggested topic lines not already present. Returns number added."""
    added = 0
    for label in suggest_milestones_from_markdown(md):
        if add_milestone(plan_id, label) is not None:
            added += 1
    return added


def build_learner_context_for_prompt(
    *,
    limit: int | None = None,
    max_total_chars: int | None = None,
) -> str | None:
    """
    Build a compact summary of recent plans and checkpoint progress for the model.

    Returns None if there is no history. Used to personalize new study plans without
    sending full prior markdown (token-efficient).
    """
    limit = limit if limit is not None else app_config.LEARNER_CONTEXT_MAX_PLANS
    max_total_chars = (
        max_total_chars
        if max_total_chars is not None
        else app_config.LEARNER_CONTEXT_MAX_CHARS
    )

    plans = list_plans(limit=limit)
    if not plans:
        return None

    lines: list[str] = [
        "Recent sessions (newest first). Use to personalize; current request wins on conflict."
    ]
    for p in plans:
        pid = int(p["id"])
        ms = list_milestones(pid)
        done = sum(1 for m in ms if m["done"])
        total = len(ms)
        goal_excerpt = (p.get("goal") or "")[:220].replace("\n", " ")
        if len(p.get("goal") or "") > 220:
            goal_excerpt += "…"
        pdf_note = f" | PDF: {p['pdf_filename']}" if p.get("pdf_filename") else ""
        cp = f"{done}/{total}" if total else "no checkpoints"
        lines.append(
            f"- [{str(p['created_at'])[:16]}] Level {p['level']}{pdf_note} | {cp} | Goal: {goal_excerpt}"
        )

    text = "\n".join(lines)
    if len(text) > max_total_chars:
        text = text[: max_total_chars - 1] + "…"
    return text
