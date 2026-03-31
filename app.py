# =============================================================================
# AI Study Agent — Streamlit UI (simple, reliable)
#   pip install -r requirements.txt
#   export OPENAI_API_KEY='sk-…'
#   streamlit run app.py
# =============================================================================

from __future__ import annotations

import html
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

import streamlit as st

import config as app_config
from agent import StudyAgentError, generate_study_plan
from agent.types import Level
from storage.memory import (
    add_milestone,
    build_learner_context_for_prompt,
    delete_milestone,
    get_plan,
    import_suggested_milestones,
    list_milestones,
    list_plans,
    save_plan,
    set_milestone_done,
)
from utils.pdf import extract_text_from_pdf
from utils.plan_content import extract_plan_sections
from utils.quiz_parse import grade_response_detail, parse_answer_chunks, parse_questions_ordered

LEVEL_OPTIONS: list[Level] = ["beginner", "intermediate", "advanced"]
LEVEL_LABELS: dict[Level, str] = {
    "beginner": "Beginner",
    "intermediate": "Intermediate",
    "advanced": "Advanced",
}


def inject_material_icons() -> None:
    """Load Material Icons from Google Fonts CDN + layout, spacing, and subtle hover motion."""
    st.markdown(
        """
        <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
        <style>
            .material-icons {
                font-family: 'Material Icons';
                font-weight: normal;
                font-style: normal;
                font-size: 23px;
                line-height: 1;
                letter-spacing: normal;
                text-transform: none;
                display: inline-block;
                white-space: nowrap;
                direction: ltr;
                -webkit-font-smoothing: antialiased;
                color: inherit;
                opacity: 0.88;
            }
            .mi-heading {
                display: flex;
                align-items: center;
                gap: 0.7rem;
                margin: 0 0 0.85rem 0;
                padding: 0.2rem 0 0.35rem 0;
                line-height: 1.4;
            }
            .mi-heading .material-icons {
                flex-shrink: 0;
                margin: 0;
                transition: transform 0.22s cubic-bezier(0.34, 1.2, 0.64, 1),
                    opacity 0.2s ease;
                transform-origin: center center;
            }
            .mi-heading:hover .material-icons {
                transform: scale(1.1) translateY(-2px);
                opacity: 1;
            }
            .mi-heading .mi-title {
                font-size: 1.25rem;
                font-weight: 600;
                color: inherit;
                letter-spacing: -0.01em;
                padding-top: 0.05em;
            }
            @media (prefers-reduced-motion: reduce) {
                .mi-heading .material-icons {
                    transition: opacity 0.15s ease;
                }
                .mi-heading:hover .material-icons {
                    transform: none;
                }
            }
            .mi-sidebar-row {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin: 0.4rem 0 0.55rem 0;
            }
            .mi-sidebar-row .material-icons {
                font-size: 18px;
                opacity: 0.88;
                flex-shrink: 0;
            }
            .mi-sidebar-row .mi-sb-label {
                font-size: 0.9375rem;
                font-weight: 600;
                color: inherit;
                line-height: 1.3;
            }
            .mi-page-title {
                display: flex;
                align-items: center;
                gap: 0.65rem;
                margin: 0 0 0.25rem 0;
            }
            .mi-page-title .material-icons {
                font-size: 32px;
                opacity: 0.9;
            }
            .mi-page-title .mi-pt-text {
                font-size: 2rem;
                font-weight: 700;
                color: inherit;
                line-height: 1.2;
                letter-spacing: -0.02em;
            }
            .mi-subhead-row {
                display: flex;
                align-items: center;
                gap: 0.55rem;
                margin: 0 0 0.6rem 0;
            }
            .mi-subhead-row .material-icons {
                font-size: 20px;
                opacity: 0.88;
            }
            .mi-subhead-row .mi-sh-text {
                font-size: 1.15rem;
                font-weight: 600;
                color: inherit;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar_section(icon: str, title: str) -> None:
    """Compact Material icon + label for sidebar (no emoji)."""
    safe_icon = html.escape(icon.strip())
    safe_title = html.escape(title)
    st.markdown(
        f'<div class="mi-sidebar-row" role="heading" aria-level="4">'
        f'<span class="material-icons" aria-hidden="true">{safe_icon}</span>'
        f'<span class="mi-sb-label">{safe_title}</span></div>',
        unsafe_allow_html=True,
    )


def _heading_with_icon(material_name: str, title: str) -> None:
    """Single-line heading: Material icon + title (material_name must be a valid Material Icons ligature)."""
    safe_icon = html.escape(material_name.strip())
    safe_title = html.escape(title)
    st.markdown(
        f'<div class="mi-heading" role="heading" aria-level="3">'
        f'<span class="material-icons" aria-hidden="true">{safe_icon}</span>'
        f'<span class="mi-title">{safe_title}</span></div>',
        unsafe_allow_html=True,
    )


def _page_title_with_icon(icon: str, title: str) -> None:
    """App title row: large Material icon + text (replaces st.title for consistent icon system)."""
    safe_icon = html.escape(icon.strip())
    safe_title = html.escape(title)
    st.markdown(
        f'<div class="mi-page-title" role="heading" aria-level="1">'
        f'<span class="material-icons" aria-hidden="true">{safe_icon}</span>'
        f'<span class="mi-pt-text">{safe_title}</span></div>',
        unsafe_allow_html=True,
    )


def _subhead_with_icon(icon: str, title: str) -> None:
    """Section subhead (main column): icon + label."""
    safe_icon = html.escape(icon.strip())
    safe_title = html.escape(title)
    st.markdown(
        f'<div class="mi-subhead-row" role="heading" aria-level="3">'
        f'<span class="material-icons" aria-hidden="true">{safe_icon}</span>'
        f'<span class="mi-sh-text">{safe_title}</span></div>',
        unsafe_allow_html=True,
    )


def _card_block(
    heading: str,
    body: str | None,
    *,
    empty_message: str,
    icon: str | None = None,
) -> None:
    if not (body and body.strip()):
        st.info(empty_message)
        return
    if icon:
        _heading_with_icon(icon, heading)
    else:
        st.subheader(heading)
    st.markdown(body.strip())


def render_header() -> None:
    _page_title_with_icon("school", "AI Study Agent")
    st.caption("Your personal AI-powered learning system — study plans, questions, and feedback.")
    st.write(
        "Generate a structured plan, optional PDF context, saved history, checkpoints, "
        "and interactive self-checks."
    )


def active_plan_row(session_state: Any) -> dict | None:
    pid = session_state.active_plan_id
    if pid is None:
        return session_state.get("preview_plan_row")
    try:
        plan_id = int(pid)
    except (TypeError, ValueError):
        session_state.active_plan_id = None
        return session_state.get("preview_plan_row")
    try:
        row = get_plan(plan_id)
        if row is not None:
            session_state.pop("preview_plan_row", None)
        return row
    except sqlite3.Error:
        return session_state.get("preview_plan_row")


def _clear_preview_plan(session_state: Any) -> None:
    session_state.pop("preview_plan_row", None)


def _safe_list_plans(limit: int = 30) -> tuple[list[dict[str, Any]], bool]:
    try:
        return list_plans(limit=limit), False
    except sqlite3.Error:
        return [], True


def render_sidebar(session_state: Any) -> None:
    with st.sidebar:
        _sidebar_section("library_books", "AI Study Agent")
        _sidebar_section("trending_up", "Your progress")
        plans, db_failed = _safe_list_plans(limit=30)
        if db_failed:
            st.warning("Could not read the local database. History may be empty until access is fixed.")
        if not plans:
            st.caption("No saved plans yet. Generate one to build history and personalized context.")
        else:
            done_total = count_total = 0
            for p in plans:
                try:
                    ms = list_milestones(int(p["id"]))
                except sqlite3.Error:
                    ms = []
                count_total += len(ms)
                done_total += sum(1 for m in ms if m["done"])
            if count_total:
                pct = round(100 * done_total / count_total)
                st.caption(f"Checkpoints: {done_total}/{count_total} ({pct}%)")
            else:
                st.caption("Add checkpoints to track completion across sessions.")

        st.divider()
        _sidebar_section("history", "Plan history")
        options: list[tuple[str, int | None]] = [("— Select a plan —", None)]
        for p in plans:
            ts = str(p["created_at"])[:16].replace("T", " ")
            g = (p["goal"] or "")[:52] + ("…" if len(p["goal"] or "") > 52 else "")
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
            if chosen_id is not None:
                _clear_preview_plan(session_state)
            st.rerun()

        st.divider()
        _sidebar_section("lock", "Environment")
        st.caption("API key via environment only (never commit secrets):")
        st.code("export OPENAI_API_KEY='sk-…'", language="bash")
        st.caption(f"Model: `{app_config.OPENAI_MODEL}` · Data: local SQLite under `data/`")


def _milestone_checkbox_callback(milestone_id: int) -> None:
    key = f"milestone_done_{milestone_id}"
    set_milestone_done(milestone_id, bool(st.session_state.get(key)))


def render_milestones_section(plan_id: int, result_md: str) -> None:
    _heading_with_icon("flag", "Checkpoints")
    st.caption("Track completion against your plan.")
    st.caption(
        "Import from the plan's **TOPICS BREAKDOWN** heading or add custom milestones. "
        "Progress persists locally."
    )
    if plan_id < 0:
        st.info("Checkpoints are available after the plan is saved to the database.")
        return
    try:
        milestones = list_milestones(plan_id)
    except sqlite3.Error:
        st.warning("Could not load checkpoints (database error).")
        return
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Import topics", key=f"import_ms_{plan_id}"):
            n = import_suggested_milestones(plan_id, result_md)
            if hasattr(st, "toast"):
                st.toast(f"Added {n} checkpoint(s)." if n else "No new topic bullets found.")
            st.rerun()
    with c2:
        with st.expander("Add checkpoint"):
            nl = st.text_input("Label", key=f"new_ms_{plan_id}", max_chars=500)
            if st.button("Save", key=f"save_ms_{plan_id}"):
                if add_milestone(plan_id, nl):
                    st.rerun()
                else:
                    st.warning("Enter a unique, non-empty label.")

    if not milestones:
        st.info("No checkpoints yet.")
        return
    for ms in milestones:
        mid = int(ms["id"])
        st.checkbox(
            ms["label"],
            value=bool(ms["done"]),
            key=f"milestone_done_{mid}",
            on_change=_milestone_checkbox_callback,
            args=(mid,),
        )
        if st.button("Remove", key=f"del_ms_{mid}", type="secondary"):
            delete_milestone(mid)
            st.session_state.pop(f"milestone_done_{mid}", None)
            st.rerun()


def _quiz_shell() -> Any:
    try:
        return st.container(border=True)
    except TypeError:
        return st.container()


def _render_questions_tab(plan_id: int, sections: dict[str, str]) -> None:
    q_body = sections.get("questions") or ""
    a_body = sections.get("answers") or ""

    _card_block(
        "Practice questions",
        q_body if q_body.strip() else None,
        empty_message="No practice questions section found in this plan.",
        icon="quiz",
    )

    parsed = parse_questions_ordered(q_body)
    answer_chunks = parse_answer_chunks(a_body, count=max(len(parsed), 5))

    if not parsed:
        st.caption(
            "For auto-grading, the model should emit `### Easy` / `### Medium` / `### Hard` "
            "with bullet questions. You can still practice manually and use the **Feedback** tab."
        )
        return

    st.divider()
    with _quiz_shell():
        _heading_with_icon("edit_note", "Your answers")
        st.caption(
            "Fill in what you know, then use **Check answers** for verdicts and open **Feedback** "
            "for explanations."
        )

        for i, item in enumerate(parsed):
            st.markdown(f"**{item['label']}** ({item['difficulty'].title()})")
            st.caption(item["text"])
            st.text_area(
                f"Your answer · {item['label']}",
                height=96,
                key=f"user_answer_{plan_id}_{i}",
                placeholder="Write your reasoning or solution here.",
                help="At least one non-empty answer is required to check.",
            )

        ca, cb = st.columns(2)
        with ca:
            check = st.button(
                "Check answers",
                type="primary",
                key=f"check_{plan_id}",
                use_container_width=True,
            )
        with cb:
            if st.button("Reset", key=f"reset_{plan_id}", use_container_width=True):
                st.session_state[f"quiz_done_{plan_id}"] = False
                st.session_state.pop(f"quiz_feedback_{plan_id}", None)
                st.session_state.pop(f"quiz_warn_{plan_id}", None)
                st.rerun()

    if check and parsed:
        answers_filled = [
            (st.session_state.get(f"user_answer_{plan_id}_{i}") or "").strip()
            for i in range(len(parsed))
        ]
        if not any(answers_filled):
            st.session_state[f"quiz_warn_{plan_id}"] = True
            st.warning("Please enter at least one answer before checking.")
        else:
            st.session_state.pop(f"quiz_warn_{plan_id}", None)
            fb: list[dict[str, Any]] = []
            for i, item in enumerate(parsed):
                user_val = answers_filled[i]
                expected = (
                    answer_chunks[i]
                    if i < len(answer_chunks)
                    else (answer_chunks[-1] if answer_chunks else "")
                )
                detail = grade_response_detail(user_val, expected)
                fb.append(
                    {
                        **detail,
                        "label": item["label"],
                        "question": item["text"],
                        "reference": expected,
                    }
                )
            st.session_state[f"quiz_feedback_{plan_id}"] = fb
            st.session_state[f"quiz_done_{plan_id}"] = True
            st.rerun()

    if st.session_state.get(f"quiz_warn_{plan_id}"):
        st.caption("You can answer just one question to get started.")

    if st.session_state.get(f"quiz_done_{plan_id}") and st.session_state.get(f"quiz_feedback_{plan_id}"):
        st.success("Graded. Open the **Feedback** tab for explanations and references.")
        fb = st.session_state[f"quiz_feedback_{plan_id}"]
        for row in fb:
            lab = html.escape(str(row.get("label", "")))
            badge = html.escape(str(row.get("badge", "")))
            st.markdown(f"- **{lab}**: {badge}")


def _render_answers_feedback_tab(plan_id: int, sections: dict[str, str]) -> None:
    _card_block(
        "Answers & explanations",
        sections.get("answers"),
        empty_message="No answers section found.",
        icon="check_circle",
    )

    fb = st.session_state.get(f"quiz_feedback_{plan_id}")
    done = st.session_state.get(f"quiz_done_{plan_id}")

    if not done or not fb:
        st.info(
            "Go to **Questions**, write your answers, then tap **Check answers** to see "
            "verdicts, explanations, and reference solutions here."
        )
        return

    _heading_with_icon("insights", "Your personalized feedback")
    st.caption("Automated comparison is indicative only — use it to steer revision.")

    for row in fb:
        v = row.get("verdict", "unknown")
        verdict_word = {
            "correct": "**Correct**",
            "partial": "**Partially correct**",
            "incorrect": "**Incorrect**",
            "empty": "**No answer submitted**",
        }.get(v, f"**{html.escape(str(v))}**")

        st.markdown(f"#### {row.get('label', '')} · {row.get('badge', '')}")
        st.markdown(f"**Question:** {row.get('question', '')}")
        st.markdown(f"**Result:** {verdict_word} — _{row.get('summary', '')}_")
        st.markdown("**Explanation**")
        st.markdown(row.get("explanation") or "")
        st.markdown("**Reference answer**")
        st.markdown(row.get("reference") or "_—_")
        st.divider()


def render_plan_tabs(plan_row: dict) -> None:
    md = plan_row.get("result_markdown") or ""
    try:
        pid = int(plan_row.get("id", 0))
    except (TypeError, ValueError):
        pid = -1
    try:
        sec = extract_plan_sections(md)
    except Exception:
        sec = {"full": md.strip(), "study_plan": md.strip() or "(Empty plan.)"}

    t1, t2, t3, t4, t5, t6, t7 = st.tabs(
        [
            "Plan",
            "Topics",
            "Learn",
            "Questions",
            "Feedback",
            "Mistakes",
            "Tips",
        ]
    )

    with t1:
        if sec.get("overview"):
            _card_block("Overview", sec["overview"], empty_message="No overview.", icon="article")
        _card_block(
            "Study plan",
            sec.get("study_plan"),
            empty_message="No study plan section — try regenerating or use the Markdown download.",
            icon="calendar_today",
        )

    with t2:
        _card_block(
            "Topics breakdown",
            sec.get("topics"),
            empty_message="No topics section found.",
            icon="menu_book",
        )

    with t3:
        _card_block(
            "Explanations",
            sec.get("explanations"),
            empty_message="No explanations section found.",
            icon="psychology",
        )

    with t4:
        _render_questions_tab(pid, sec)

    with t5:
        _render_answers_feedback_tab(pid, sec)

    with t6:
        _card_block(
            "Common mistakes",
            sec.get("mistakes"),
            empty_message="No mistakes section found.",
            icon="warning",
        )

    with t7:
        _card_block(
            "Smart tips",
            sec.get("tips"),
            empty_message="No tips section found.",
            icon="lightbulb",
        )


class _SpinnerStatus:
    def write(self, text: str) -> None:
        st.caption(text)

    def update(self, **kwargs: object) -> None:  # noqa: ARG002
        pass


@contextmanager
def _generation_progress() -> Iterator[object]:
    _msg = "Generating your personalized study plan..."
    if hasattr(st, "status"):
        with st.status(_msg, expanded=True) as status:
            yield status
    else:
        with st.spinner(_msg):
            yield _SpinnerStatus()


def _init_session_state() -> None:
    if "active_plan_id" not in st.session_state:
        st.session_state.active_plan_id = None
    if "last_error" not in st.session_state:
        st.session_state.last_error = None
    if "show_study_success" not in st.session_state:
        st.session_state.show_study_success = False


def main() -> None:
    st.set_page_config(
        page_title="AI Study Agent",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _init_session_state()
    inject_material_icons()
    render_sidebar(st.session_state)
    render_header()

    left, right = st.columns((1, 1.12), gap="large")

    with left:
        _subhead_with_icon("post_add", "New study plan")
        st.caption("Describe what you want to learn.")
        with st.form("study_form", clear_on_submit=False):
            goal = st.text_area(
                "What do you want to learn?",
                height=118,
                placeholder="e.g. Master eigenvalues for my exam.",
                help="Required. Optional PDF adds grounded context.",
            )
            st.file_uploader(
                "Reference PDF (optional)",
                type=["pdf"],
                help="Text extraction only; scanned PDFs may need OCR first.",
                key="pdf_upload",
            )
            c1, c2 = st.columns(2)
            with c1:
                level_key = st.selectbox(
                    "Experience level",
                    options=LEVEL_OPTIONS,
                    format_func=lambda x: LEVEL_LABELS[x],
                )
            with c2:
                time_available = st.text_input(
                    "Time you can invest",
                    placeholder="e.g. 2 weeks, 1 hr/day",
                )
            submitted = st.form_submit_button(
                "Generate study plan",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not (goal or "").strip():
                st.warning("Please enter a study goal.")
            else:
                st.session_state.last_error = None
                upload = st.session_state.get("pdf_upload")
                ref_text = pdf_name = None
                if upload is not None:
                    try:
                        ref_text = extract_text_from_pdf(upload.getvalue())
                        pdf_name = upload.name
                    except StudyAgentError as e:
                        st.session_state.last_error = str(e)

                if not st.session_state.last_error:
                    try:
                        with _generation_progress() as status:
                            status.write("Loading learner history for personalization…")
                            try:
                                learner_ctx = build_learner_context_for_prompt()
                            except (sqlite3.Error, OSError, ValueError):
                                learner_ctx = None
                            status.write("Calling OpenAI…")
                            result = generate_study_plan(
                                goal=goal,
                                level=level_key,
                                time_available=time_available,
                                reference_material=ref_text,
                                learner_context=learner_ctx,
                            )
                            status.write("Saving to local history…")
                            status_done = "Done"
                            try:
                                pid = save_plan(
                                    goal=goal,
                                    level=level_key,
                                    time_available=time_available,
                                    result_markdown=result,
                                    pdf_filename=pdf_name,
                                )
                                st.session_state.active_plan_id = pid
                                _clear_preview_plan(st.session_state)
                                st.session_state.show_study_success = True
                            except sqlite3.Error as db_exc:
                                status_done = "Generated — save failed"
                                st.session_state.preview_plan_row = {
                                    "id": -1,
                                    "result_markdown": result,
                                    "goal": (goal or "").strip(),
                                    "level": level_key,
                                    "time_available": (time_available or "").strip(),
                                    "pdf_filename": pdf_name,
                                }
                                st.session_state.active_plan_id = None
                                st.session_state.last_error = (
                                    "Your plan was generated but could not be saved to the local database "
                                    f"(check `data/` permissions). You can still review it below. ({db_exc})"
                                )
                                st.session_state.show_study_success = True
                            status.update(label=status_done, state="complete")
                    except StudyAgentError as e:
                        st.session_state.last_error = str(e)

    plan_row = active_plan_row(st.session_state)

    with right:
        _subhead_with_icon("assessment", "Output & progress")
        if st.session_state.last_error:
            st.error(st.session_state.last_error)
        if plan_row:
            if st.session_state.pop("show_study_success", False):
                if st.session_state.last_error:
                    st.success(
                        "Study plan generated — review below. It was not saved to history; "
                        "see the error message for details."
                    )
                else:
                    st.success("Study plan generated and saved successfully.")
                if hasattr(st, "toast"):
                    st.toast("Use the tabs below to explore your plan.")

            meta = [
                f"**Level:** {plan_row['level']}",
                f"**Time:** {plan_row['time_available']}",
            ]
            if plan_row.get("pdf_filename"):
                meta.append(f"**PDF:** {plan_row['pdf_filename']}")
            st.markdown(" · ".join(meta))
            g = plan_row["goal"] or ""
            st.caption(g[:300] + ("…" if len(g) > 300 else ""))

            dc, pc = st.columns((1.08, 1), gap="medium")
            with dc:
                _subhead_with_icon("dashboard", "Learning workspace")
                render_plan_tabs(plan_row)
                st.download_button(
                    "Download full Markdown",
                    plan_row.get("result_markdown") or "",
                    file_name="study_plan.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with pc:
                rid = plan_row.get("id", 0)
                try:
                    pid_int = int(rid)
                except (TypeError, ValueError):
                    pid_int = 0
                try:
                    _ms_host = st.container(border=True)
                except TypeError:
                    _ms_host = st.container()
                with _ms_host:
                    render_milestones_section(pid_int, plan_row.get("result_markdown") or "")
        elif not st.session_state.last_error:
            st.info(
                f"Generate a plan or pick one from the sidebar. Model: **{app_config.OPENAI_MODEL}**."
            )

    st.divider()
    st.caption(
        f"AI Study Agent · OpenAI via `OPENAI_API_KEY` · Model `{app_config.OPENAI_MODEL}` · "
        "Logic in `agent/`, `storage/`, `utils/`."
    )


run = main

if __name__ == "__main__":
    main()
