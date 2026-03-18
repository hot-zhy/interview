"""Shared UI styles and CSS injection for consistent look across pages."""

import streamlit as st


def inject_global_styles():
    """Inject global CSS for improved UI/UX."""
    st.markdown("""
    <style>
    /* 全局优化 - 清爽浅色主题 */
    .stApp {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 50%, #f8fafc 100%);
    }
    
    /* 主标题样式 */
    h1 {
        font-weight: 700 !important;
        letter-spacing: -0.02em;
        color: #1e293b !important;
    }
    
    h2, h3 {
        color: #334155 !important;
        font-weight: 600 !important;
    }
    
    /* 卡片式容器 */
    .stExpander {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* 按钮优化 */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
    }
    
    /* 输入框 */
    .stTextInput > div > div > input,
    .stTextArea > div > div {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    
    /* 指标卡片 */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
    }
    
    /* 侧边栏 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border-right: 1px solid #e2e8f0;
    }
    
    /* 页面内边距 */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* 导航卡片 */
    .nav-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
        transition: all 0.2s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .nav-card:hover {
        border-color: #6366f1;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.15);
    }
    
    /* 欢迎横幅 */
    .welcome-banner {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        color: white;
        box-shadow: 0 8px 32px rgba(99, 102, 241, 0.25);
    }
    
    /* 分割线 */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
        margin: 24px 0;
    }
    
    /* 表单容器 */
    .stForm {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 24px;
        background: #ffffff;
    }
    
    /* 加载动画增强 - 让 spinner 更醒目 */
    [data-testid="stSpinner"] {
        margin: 1rem 0 !important;
    }
    [data-testid="stSpinner"] > div {
        border-color: #6366f1 !important;
        border-right-color: transparent !important;
    }
    </style>
    """, unsafe_allow_html=True)


def render_metric_card(label: str, value: str, delta: str = None):
    """Render a styled metric display."""
    delta_html = f'<span style="font-size: 0.9rem; color: #64748b;">{delta}</span>' if delta else ""
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    ">
        <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 4px;">{label}</div>
        <div style="font-size: 1.5rem; font-weight: 700; color: #1e293b;">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)
