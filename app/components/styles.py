"""Shared UI styles and CSS injection for consistent look across pages."""

import streamlit as st


def inject_global_styles():
    """Inject global CSS for a tech-forward card UI."""
    st.markdown("""
    <style>
    :root {
        --surface: rgba(255, 255, 255, 0.84);
        --surface-strong: rgba(255, 255, 255, 0.96);
        --line: rgba(116, 139, 171, 0.24);
        --ink: #172033;
        --muted: #667085;
        --accent: #2563eb;
        --accent-2: #0891b2;
        --accent-3: #7c3aed;
    }

    .stApp {
        background:
            linear-gradient(135deg, rgba(37, 99, 235, 0.10) 0%, rgba(8, 145, 178, 0.07) 38%, rgba(124, 58, 237, 0.08) 72%, rgba(248, 250, 252, 1) 100%),
            #f6f8fc;
        color: var(--ink);
    }

    h1 {
        color: var(--ink) !important;
        font-weight: 780 !important;
        letter-spacing: 0;
    }

    h2, h3 {
        color: #243047 !important;
        font-weight: 720 !important;
        letter-spacing: 0;
    }

    p, li, label, span {
        letter-spacing: 0;
    }

    .block-container {
        max-width: 1280px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    .stExpander,
    .stForm,
    .nav-card {
        background: var(--surface-strong);
        border: 1px solid var(--line);
        border-radius: 8px;
        box-shadow: 0 18px 50px rgba(33, 56, 96, 0.08);
    }

    .stExpander {
        margin-bottom: 12px;
    }

    .stForm {
        padding: 24px;
    }

    .stButton > button {
        border: 1px solid rgba(37, 99, 235, 0.24);
        border-radius: 8px;
        font-weight: 680;
        letter-spacing: 0;
        transition: all 0.16s ease;
    }

    .stButton > button:hover {
        border-color: rgba(8, 145, 178, 0.52);
        box-shadow: 0 10px 28px rgba(37, 99, 235, 0.16);
        transform: translateY(-1px);
    }

    .stTextInput > div > div > input,
    .stTextArea > div > div,
    .stSelectbox > div > div,
    .stNumberInput > div > div {
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid rgba(116, 139, 171, 0.24);
        border-radius: 8px;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
    }

    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 780 !important;
    }

    [data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, rgba(15, 23, 42, 0.98) 0%, rgba(21, 31, 55, 0.96) 48%, rgba(20, 42, 60, 0.96) 100%);
        border-right: 1px solid rgba(148, 163, 184, 0.22);
        box-shadow: 18px 0 60px rgba(15, 23, 42, 0.18);
    }

    [data-testid="stSidebarNav"] {
        display: none;
    }

    [data-testid="stSidebar"] * {
        color: rgba(241, 245, 249, 0.92);
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] small {
        color: rgba(203, 213, 225, 0.78) !important;
    }

    [data-testid="stSidebar"] hr {
        background: linear-gradient(90deg, transparent, rgba(125, 211, 252, 0.42), transparent);
        margin: 18px 0;
    }

    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(125, 211, 252, 0.28);
        color: #f8fafc;
    }

    [data-testid="stSidebar"] .stButton > button[kind="primary"],
    [data-testid="stSidebar"] .stButton > button:focus {
        background: linear-gradient(135deg, #2563eb 0%, #0891b2 100%);
        border-color: rgba(255, 255, 255, 0.28);
    }

    [data-testid="stSidebar"] a {
        border-radius: 8px;
        margin: 4px 0;
        transition: background 0.16s ease, transform 0.16s ease;
    }

    [data-testid="stSidebar"] a:hover {
        background: rgba(125, 211, 252, 0.12);
        transform: translateX(2px);
    }

    .nav-card {
        margin: 8px 0;
        padding: 20px;
        transition: all 0.2s ease;
    }

    .nav-card:hover {
        border-color: rgba(37, 99, 235, 0.34);
        box-shadow: 0 18px 46px rgba(37, 99, 235, 0.14);
    }

    .welcome-banner {
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.94) 0%, rgba(8, 145, 178, 0.9) 58%, rgba(124, 58, 237, 0.86) 100%);
        border: 1px solid rgba(255, 255, 255, 0.24);
        border-radius: 8px;
        box-shadow: 0 24px 70px rgba(37, 99, 235, 0.24);
        color: white;
        margin-bottom: 24px;
        padding: 24px;
    }

    hr {
        background: linear-gradient(90deg, transparent, rgba(116, 139, 171, 0.36), transparent);
        border: none;
        height: 1px;
        margin: 24px 0;
    }

    [data-testid="stSpinner"] {
        margin: 1rem 0 !important;
    }

    [data-testid="stSpinner"] > div {
        border-color: #0891b2 !important;
        border-right-color: transparent !important;
    }
    </style>
    """, unsafe_allow_html=True)


def render_metric_card(label: str, value: str, delta: str = None):
    """Render a styled metric display."""
    delta_html = f'<span style="font-size: 0.9rem; color: #667085;">{delta}</span>' if delta else ""
    st.markdown(f"""
    <div style="
        background: rgba(255,255,255,0.94);
        border: 1px solid rgba(116,139,171,0.24);
        border-radius: 8px;
        padding: 16px 20px;
        text-align: center;
        box-shadow: 0 18px 50px rgba(33,56,96,0.08);
    ">
        <div style="font-size: 0.85rem; color: #667085; margin-bottom: 4px;">{label}</div>
        <div style="font-size: 1.5rem; font-weight: 780; color: #172033;">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)
