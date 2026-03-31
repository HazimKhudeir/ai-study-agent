#!/usr/bin/env python3
"""
Step-by-step verification of AI Study Agent features (no live OpenAI call).

Run from project root:  python3 tests/verify_project.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Project root on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# -----------------------------------------------------------------------------
# Step 0: Isolated SQLite for storage tests
# -----------------------------------------------------------------------------
import config as app_config

_tmp_data = Path(tempfile.mkdtemp())
app_config.DATA_DIR = _tmp_data

# Imports after DATA_DIR redirect
from agent.errors import StudyAgentError  # noqa: E402
from agent.service import generate_study_plan  # noqa: E402
from storage import memory as mem  # noqa: E402
from utils.markdown_sections import split_markdown_by_h1  # noqa: E402
from utils.pdf import extract_text_from_pdf  # noqa: E402
from utils.plan_content import extract_plan_sections  # noqa: E402
from utils.quiz_parse import (  # noqa: E402
    grade_response_detail,
    parse_answer_chunks,
    parse_questions_ordered,
)
from utils.validation import validate_study_inputs  # noqa: E402


def _ok(name: str) -> None:
    print(f"  ✓ {name}")


def _fail(name: str, err: Exception) -> None:
    print(f"  ✗ {name}: {err}")
    raise err


def main() -> int:
    print("AI Study Agent — automated verification\n")

    # --- 1. Input validation (empty / invalid) ---
    print("1. Input validation")
    try:
        validate_study_inputs("", "1 day")
        _fail("empty goal should raise", AssertionError("expected StudyAgentError"))
    except StudyAgentError:
        _ok("empty goal rejected")

    try:
        validate_study_inputs("goal", "")
        _fail("empty time should raise", AssertionError("expected StudyAgentError"))
    except StudyAgentError:
        _ok("empty time rejected")

    validate_study_inputs("Learn Python", "3 days")
    _ok("valid goal + time accepted")

    # --- 2. PDF extraction errors ---
    print("\n2. PDF handling")
    try:
        extract_text_from_pdf(b"")
        _fail("empty PDF bytes", AssertionError("expected StudyAgentError"))
    except StudyAgentError:
        _ok("empty PDF rejected")

    # --- 3. Markdown section split (tabs / cards) ---
    print("\n3. Markdown sections (Study plan / Topics / …)")
    sample = """# 🚀 STUDY PLAN
Day 1 — 30 min: read

# 📚 TOPICS BREAKDOWN
- Topic A

# 📝 PRACTICE QUESTIONS
### 🟢 Easy
- Q1
"""
    parts = split_markdown_by_h1(sample)
    assert len(parts) >= 2, parts
    _ok(f"split_markdown_by_h1 → {len(parts)} sections")

    sec = extract_plan_sections(sample)
    assert sec.get("study_plan") and "Day 1" in sec["study_plan"]
    assert sec.get("topics") and "Topic A" in sec["topics"]
    assert sec.get("questions") and "Q1" in sec["questions"]
    _ok("extract_plan_sections maps H1 → study_plan, topics, questions")

    # --- 4. Quiz parse + grading ---
    print("\n4. Interactive quiz (parse + grade)")
    q_body = sec.get("questions", "")
    qs = parse_questions_ordered(q_body)
    assert len(qs) >= 1 and qs[0]["label"] == "Easy 1"
    _ok("parse_questions_ordered finds Easy 1")

    ans = parse_answer_chunks("- A1\n- A2\n", count=2)
    assert len(ans) == 2
    _ok("parse_answer_chunks splits bullets")

    g = grade_response_detail("A1", "A1")
    assert g["verdict"] == "correct"
    _ok("grade_response_detail marks exact match correct")

    g2 = grade_response_detail("", "anything")
    assert g2["verdict"] == "empty"
    _ok("grade_response_detail handles empty answer")

    # --- 5. SQLite: save plan, list, milestones ---
    print("\n5. Storage (plans + milestones)")
    md = "# 🚀 STUDY PLAN\n\nTest content\n"
    pid = mem.save_plan("Test goal", "beginner", "1 day", md, None)
    assert pid > 0
    _ok(f"save_plan → id={pid}")

    row = mem.get_plan(pid)
    assert row and row["result_markdown"] == md
    _ok("get_plan retrieves row")

    plans = mem.list_plans(limit=10)
    assert any(p["id"] == pid for p in plans)
    _ok("list_plans includes new plan")

    mem.add_milestone(pid, "Checkpoint 1")
    ms = mem.list_milestones(pid)
    assert len(ms) == 1
    _ok("add_milestone + list_milestones")

    ctx = mem.build_learner_context_for_prompt(limit=3)
    assert ctx and "Test goal" in ctx
    _ok("build_learner_context_for_prompt")

    # --- 6. OpenAI path (mocked — no network) ---
    print("\n6. Study plan generation (mocked API)")
    fake = MagicMock()
    fake.choices = [
        MagicMock(message=MagicMock(content="# 🚀 STUDY PLAN\n\nMock day 1\n\n# 📚 TOPICS BREAKDOWN\n- T\n"))
    ]
    mock_api = MagicMock()
    mock_api.chat.completions.create.return_value = fake

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-fake"}):
        with patch("agent.service.OpenAI", return_value=mock_api):
            out = generate_study_plan(
                "Learn X",
                "beginner",
                "2 days",
                client=mock_api,
            )
    assert "Mock day 1" in out
    mock_api.chat.completions.create.assert_called_once()
    _ok("generate_study_plan calls API and returns markdown")

    # --- 7. App module import (Streamlit + UI wiring) ---
    print("\n7. App module load")
    try:
        import app as app_module  # noqa: F401

        for name in (
            "main",
            "render_plan_tabs",
            "active_plan_row",
            "_safe_list_plans",
            "inject_styles",
        ):
            assert hasattr(app_module, name), name
        _ok("app.py exports main + UI helpers")
    except Exception as e:
        _fail("import app", e)

    # --- 8. CLI entry ---
    print("\n8. CLI module")
    import study_agent  # noqa: F401

    assert hasattr(study_agent, "main")
    _ok("study_agent.py importable")

    print("\n" + "=" * 50)
    print("All automated checks passed.")
    print("Manual: run `streamlit run app.py` and click through tabs + Check answers.")
    print(f"Temp DB used: {_tmp_data}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as e:
        print(f"\nAssertion failed: {e}")
        raise SystemExit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        raise SystemExit(1)
