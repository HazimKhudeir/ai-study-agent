"""
Reusable Streamlit fragments: plan sections, milestones, sidebar history.

Keeps ``streamlit_app.py`` focused on orchestration and session flow.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from storage.memory import (
    add_milestone,
    delete_milestone,
    get_plan,
    import_suggested_milestones,
    list_milestones,
    list_plans,
    set_milestone_done,
)
from utils.markdown_sections import section_card_open_html, split_markdown_by_h1


def render_header() -> None:
    st.markdown("# Study Studio")
    st.markdown(
        '<p class="hero-sub">Production-style study planning: PDF context, adaptive prompting, '
        "saved history, and checkpoint progress — with clear errors when something goes wrong.</p>",
        unsafe_allow_html=True,
    )


def render_plan_in_cards(markdown_content: str) -> None:
    """Render each top-level markdown section inside a styled card."""
    sections = split_markdown_by_h1(markdown_content)
    for title, body in sections:
        st.markdown(section_card_open_html(title), unsafe_allow_html=True)
        st.markdown(body)
        st.markdown("</div>", unsafe_allow_html=True)


def milestone_checkbox_callback(milestone_id: int) -> None:
    key = f"milestone_done_{milestone_id}"
    set_milestone_done(milestone_id, bool(st.session_state.get(key)))


def render_milestones_section(plan_id: int, result_md: str) -> None:
    st.markdown('<p class="panel-title">Checkpoints</p>', unsafe_allow_html=True)
    st.caption(
        "Track progress here. Import suggested items from **# 📚 TOPICS BREAKDOWN** (or legacy "
        "**# Topics**) or add your own. Completion is saved locally."
    )

    milestones = list_milestones(plan_id)
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("Import topics as checkpoints", key=f"import_ms_{plan_id}"):
            n = import_suggested_milestones(plan_id, result_md)
            if n:
                st.success(f"Added {n} checkpoint(s).")
            else:
                st.info(
                    "No bullet-style topics found under “# 📚 TOPICS BREAKDOWN”, or they already exist."
                )
            st.rerun()
    with col_b:
        with st.expander("Add checkpoint"):
            new_label = st.text_input("Label", key=f"new_ms_label_{plan_id}", max_chars=500)
            if st.button("Save", key=f"save_ms_{plan_id}"):
                if add_milestone(plan_id, new_label):
                    st.rerun()
                else:
                    st.warning("Enter a non-empty label, or avoid duplicates.")

    if not milestones:
        st.info("No checkpoints yet — import from the plan or add your own.")
        return

    for ms in milestones:
        mid = int(ms["id"])
        st.checkbox(
            ms["label"],
            value=bool(ms["done"]),
            key=f"milestone_done_{mid}",
            on_change=milestone_checkbox_callback,
            args=(mid,),
        )
        if st.button("Remove", key=f"del_ms_{mid}", type="secondary"):
            delete_milestone(mid)
            if f"milestone_done_{mid}" in st.session_state:
                del st.session_state[f"milestone_done_{mid}"]
            st.rerun()


def render_sidebar(session_state: Any) -> None:
    """
    History picker, aggregate stats, and setup hints.

    ``session_state`` should be ``st.session_state``.
    """
    with st.sidebar:
        st.markdown("### Your progress")
        plans = list_plans(limit=30)
        if not plans:
            st.caption("No saved plans yet. Generate one to build history and memory.")
        else:
            done_total = 0
            count_total = 0
            for p in plans:
                ms = list_milestones(int(p["id"]))
                count_total += len(ms)
                done_total += sum(1 for m in ms if m["done"])
            if count_total:
                pct = round(100 * done_total / count_total)
                st.markdown(
                    f'<span class="stat-pill">Checkpoints: {done_total}/{count_total} ({pct}%)</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Add checkpoints to track completion across sessions.")

        st.divider()
        st.markdown("### Plan history")
        options: list[tuple[str, int | None]] = [("— Select a plan —", None)]
        for p in plans:
            ts = str(p["created_at"])[:16].replace("T", " ")
            g = (p["goal"] or "")[:52]
            if len(p["goal"] or "") > 52:
                g += "…"
            options.append((f"{ts} · {g}", int(p["id"])))

        labels = [o[0] for o in options]
        ids = [o[1] for o in options]
        known_ids = {i for i in ids if i is not None}
        if session_state.active_plan_id is not None and session_state.active_plan_id not in known_ids:
            session_state.active_plan_id = None
            st.rerun()

        def _ix_from_id() -> int:
            cur = session_state.active_plan_id
            if cur is None:
                return 0
            try:
                return ids.index(int(cur))
            except ValueError:
                return 0

        choice = st.selectbox(
            "Open a saved plan",
            options=labels,
            index=_ix_from_id(),
            label_visibility="collapsed",
        )
        chosen_id = ids[labels.index(choice)]
        if chosen_id != session_state.active_plan_id:
            session_state.active_plan_id = chosen_id
            session_state.last_error = None
            st.rerun()

        st.divider()
        st.markdown("### Setup")
        st.caption("Environment variable (never commit keys):")
        st.code("export OPENAI_API_KEY='sk-…'", language="bash")
        st.caption("Model is set in `config.py` (default: gpt-4o-mini).")


def active_plan_row(session_state) -> dict | None:
    """Return the currently selected plan row from storage, if any."""
    pid = session_state.active_plan_id
    if pid is None:
        return None
    return get_plan(int(pid))
