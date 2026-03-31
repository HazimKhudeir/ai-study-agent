"""
Tabbed plan viewer, card layout, and interactive practice check.

Separated from ``streamlit_app`` to keep orchestration readable.
"""

from __future__ import annotations

import streamlit as st

from utils.markdown_sections import section_card_open_html
from utils.plan_content import extract_plan_sections
from utils.quiz_parse import grade_response, parse_answer_chunks, parse_questions_ordered


def _card_block(heading: str, body: str | None, *, empty_message: str) -> None:
    """Render one markdown block inside a styled card."""
    if not (body and body.strip()):
        st.info(empty_message)
        return
    st.markdown(section_card_open_html(heading), unsafe_allow_html=True)
    st.markdown(body.strip())
    st.markdown("</div>", unsafe_allow_html=True)


def render_plan_tabs(plan_row: dict) -> None:
    """
    Display the saved plan in tabs with cards and an interactive question checker.

    Expects a row dict from ``storage.memory.get_plan`` (must include ``id``, ``result_markdown``).
    """
    md = plan_row.get("result_markdown") or ""
    pid = int(plan_row["id"])
    sections = extract_plan_sections(md)

    tab_plan, tab_expl, tab_q, tab_ans, tab_mt = st.tabs(
        [
            "📋 Study plan",
            "🧠 Explanations",
            "📝 Questions",
            "✅ Answers",
            "⚠️ Mistakes & tips",
        ]
    )

    with tab_plan:
        if sections.get("overview"):
            _card_block(
                "📌 Overview",
                sections["overview"],
                empty_message="No overview content.",
            )
        _card_block(
            "🚀 Study plan",
            sections.get("study_plan"),
            empty_message="No study plan section found. Try regenerating or check the raw download.",
        )
        _card_block(
            "📚 Topics breakdown",
            sections.get("topics"),
            empty_message="No topics section found.",
        )

    with tab_expl:
        _card_block(
            "🧠 Explanations",
            sections.get("explanations"),
            empty_message="No explanations section found.",
        )

    with tab_q:
        _render_questions_tab(pid, sections)

    with tab_ans:
        _card_block(
            "✅ Answers & explanations",
            sections.get("answers"),
            empty_message="No answers section found.",
        )

    with tab_mt:
        _card_block(
            "⚠️ Common mistakes",
            sections.get("mistakes"),
            empty_message="No mistakes section found.",
        )
        _card_block(
            "💡 Smart tips",
            sections.get("tips"),
            empty_message="No tips section found.",
        )


def _render_questions_tab(plan_id: int, sections: dict[str, str]) -> None:
    q_body = sections.get("questions") or ""
    a_body = sections.get("answers") or ""

    _card_block(
        "📝 Practice questions",
        q_body if q_body.strip() else None,
        empty_message="No practice questions section found.",
    )

    parsed = parse_questions_ordered(q_body)
    answer_chunks = parse_answer_chunks(a_body, count=max(len(parsed), 5))

    if not parsed:
        st.caption(
            "When questions use `### 🟢 Easy` / `### 🟡 Medium` / `### 🔴 Hard` with bullet "
            "lines, this tab can score your responses. You can still answer on paper and use "
            "the **Answers** tab."
        )
        return

    st.markdown("---")
    st.markdown("##### ✍️ Your answers")
    st.caption("Type a response for each question, then **Check answers** for instant feedback.")

    for i, item in enumerate(parsed):
        label = item["label"]
        diff = item["difficulty"].title()
        st.markdown(f"**{label}** ({diff})")
        st.caption(item["text"])
        st.text_area(
            f"Your answer — {label}",
            height=88,
            key=f"user_answer_{plan_id}_{i}",
            placeholder="Write your answer here…",
        )

    col_a, col_b = st.columns(2)
    with col_a:
        check = st.button("Check answers", type="primary", key=f"check_answers_{plan_id}")
    with col_b:
        if st.button("Reset check", key=f"reset_check_{plan_id}"):
            st.session_state[f"quiz_done_{plan_id}"] = False
            st.rerun()

    if check:
        st.session_state[f"quiz_done_{plan_id}"] = True

    if st.session_state.get(f"quiz_done_{plan_id}"):
        st.success("Feedback ready — compare each block with the **Answers** tab for full context.")
        for i, item in enumerate(parsed):
            user_val = st.session_state.get(f"user_answer_{plan_id}_{i}", "") or ""
            expected = (
                answer_chunks[i]
                if i < len(answer_chunks)
                else (answer_chunks[-1] if answer_chunks else "")
            )
            status, note = grade_response(user_val, expected)
            st.markdown(f"##### {item['label']} — {status}")
            st.caption(note)
            st.markdown("**Reference answer**")
            st.markdown(expected or "_No matching answer chunk parsed — open the Answers tab._")
            st.divider()
