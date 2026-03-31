"""Inject global CSS for layout, typography, and section cards."""

from __future__ import annotations

import streamlit as st


def inject_styles() -> None:
    """Apply theme-aligned styles (Streamlit runs in light/dark; we target a dark studio look)."""
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=JetBrains+Mono:wght@400;500&display=swap');

            html, body, [class*="css"] {
                font-family: 'DM Sans', system-ui, sans-serif;
            }
            .stApp {
                background: radial-gradient(1200px 600px at 10% -10%, rgba(45, 212, 191, 0.1), transparent),
                            radial-gradient(900px 500px at 100% 0%, rgba(99, 102, 241, 0.12), transparent),
                            linear-gradient(165deg, #0b1220 0%, #111827 42%, #0f172a 100%);
            }
            [data-testid="stHeader"] {
                background: rgba(15, 23, 42, 0.88);
                backdrop-filter: blur(10px);
            }
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, rgba(17, 24, 39, 0.98) 0%, rgba(15, 23, 42, 0.99) 100%);
                border-right: 1px solid rgba(148, 163, 184, 0.12);
            }
            [data-testid="stSidebar"] .block-container {
                padding-top: 1.5rem;
            }
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 3rem;
                max-width: 1200px;
            }
            h1 {
                font-weight: 700 !important;
                letter-spacing: -0.03em;
                background: linear-gradient(90deg, #f8fafc 0%, #99f6e4 42%, #a5b4fc 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .hero-sub {
                color: #94a3b8 !important;
                font-size: 1.06rem !important;
                line-height: 1.55;
                max-width: 44rem;
                margin-bottom: 1.25rem;
            }
            div[data-testid="stForm"] {
                background: rgba(30, 41, 59, 0.42);
                border: 1px solid rgba(148, 163, 184, 0.14);
                border-radius: 16px;
                padding: 1.35rem 1.35rem 1.55rem;
                backdrop-filter: blur(12px);
                margin-bottom: 0.5rem;
            }
            .panel-title {
                color: #e2e8f0;
                font-weight: 600;
                font-size: 0.98rem;
                margin: 0 0 0.65rem 0;
                letter-spacing: 0.02em;
            }
            .stat-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                background: rgba(45, 212, 191, 0.1);
                color: #5eead4;
                border: 1px solid rgba(45, 212, 191, 0.25);
                border-radius: 999px;
                padding: 0.28rem 0.85rem;
                font-size: 0.8rem;
                font-weight: 500;
            }
            .section-card {
                background: rgba(15, 23, 42, 0.72);
                border: 1px solid rgba(148, 163, 184, 0.14);
                border-radius: 14px;
                padding: 1rem 1.2rem 1.2rem;
                margin-bottom: 1.15rem;
            }
            .section-card-title {
                color: #f1f5f9;
                font-weight: 700;
                font-size: 1.05rem;
                text-transform: none;
                letter-spacing: 0.02em;
                margin: 0 0 0.75rem 0;
                padding-bottom: 0.5rem;
                border-bottom: 1px solid rgba(148, 163, 184, 0.18);
            }
            .section-card .stMarkdown p, .section-card .stMarkdown li {
                color: #e2e8f0 !important;
                line-height: 1.55;
            }
            .section-card .stMarkdown ul, .section-card .stMarkdown ol {
                margin-top: 0.35rem;
                margin-bottom: 0.65rem;
                padding-left: 1.2rem;
            }
            .section-card .stMarkdown strong {
                color: #fef3c7 !important;
                font-weight: 600;
            }
            .section-card .stMarkdown h3 {
                color: #a5b4fc !important;
                font-size: 0.95rem !important;
                margin-top: 0.85rem !important;
                margin-bottom: 0.4rem !important;
            }
            div[data-testid="stExpander"] {
                background: rgba(30, 41, 59, 0.35);
                border: 1px solid rgba(148, 163, 184, 0.12);
                border-radius: 12px;
            }
            div[data-testid="stSpinner"] + * {
                margin-top: 0.5rem;
            }
            div[data-testid="stTabs"] {
                margin-top: 0.35rem;
            }
            div[data-testid="stTabs"] button[data-baseweb="tab"] {
                font-weight: 600 !important;
                font-size: 0.9rem !important;
                letter-spacing: 0.01em;
            }
            div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
                background-color: rgba(45, 212, 191, 0.35) !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
