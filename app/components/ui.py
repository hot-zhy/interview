"""Common UI components."""
import streamlit as st
import pandas as pd


def inject_common_styles():
    """Inject shared spacing and typography (no color change)."""
    st.markdown("""
    <style>
    /* Section spacing */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    h1 { margin-bottom: 0.5rem; font-size: 1.85rem; }
    h2, h3 { margin-top: 1.25rem; margin-bottom: 0.6rem; }
    /* Form and widget spacing */
    [data-testid="stVerticalBlock"] > div { gap: 0.5rem; }
    [data-testid="column"] + [data-testid="column"] { margin-left: 0.5rem; }
    /* Chat messages: consistent padding */
    [data-testid="stChatMessage"] { padding: 0.75rem 1rem; margin-bottom: 0.5rem; }
    /* Buttons in columns: full width where used */
    .stButton > button { font-weight: 500; min-height: 2.25rem; }
    /* Sidebar section spacing */
    [data-testid="stSidebar"] .stMarkdown { margin-bottom: 0.5rem; }
    /* Metric cards: tighter on small screens */
    [data-testid="stMetricValue"] { font-size: 1.25rem; }
    </style>
    """, unsafe_allow_html=True)


def show_evaluation(evaluation: dict):
    """Display evaluation results."""
    scores = evaluation.get("scores", {})
    overall = evaluation.get("overall_score", 0.0)
    
    st.markdown("### 📊 评价结果")
    
    # Create a table for scores
    score_data = {
        "评分项": ["综合得分", "正确性", "深度", "清晰度", "实用性", "权衡分析"],
        "得分": [
            f"{overall:.2f}",
            f"{scores.get('correctness', 0):.2f}",
            f"{scores.get('depth', 0):.2f}",
            f"{scores.get('clarity', 0):.2f}",
            f"{scores.get('practicality', 0):.2f}",
            f"{scores.get('tradeoffs', 0):.2f}"
        ]
    }
    df_scores = pd.DataFrame(score_data)
    
    # Display as a simple table with custom styling
    st.markdown("""
    <style>
    .score-table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
    }
    .score-table th, .score-table td {
        padding: 8px 12px;
        text-align: left;
        border-bottom: 1px solid #ddd;
    }
    .score-table th {
        background-color: #f8f9fa;
        font-weight: bold;
        border-top: 2px solid #333;
        border-bottom: 2px solid #333;
    }
    .score-table tr:last-child td {
        border-bottom: 2px solid #333;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Use st.table for a simple table display
    st.table(df_scores)
    
    # Feedback
    st.markdown("#### 💬 反馈")
    st.info(evaluation.get("feedback", "无反馈"))
    
    # Missing points
    missing = evaluation.get("missing_points", [])
    if missing:
        st.markdown("#### 📌 缺失知识点")
        for point in missing[:5]:
            st.text(f"- {point}")

