"""Streamlit main app."""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from app.components.auth_utils import init_session_state
from app.components.auth_loader import load_auth_on_page_load
from app.components.styles import inject_global_styles

# Page configuration
st.set_page_config(
    page_title="AI 面试系统",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject global styles
inject_global_styles()

# Load auth from localStorage first (before init_session_state)
load_auth_on_page_load()

# Initialize session state
init_session_state()

# Main app
def main():
    # Sidebar - 快捷导航
    with st.sidebar:
        st.markdown("### 🎯 快捷导航")
        if st.session_state.authenticated:
            st.caption(f"👤 {st.session_state.user_email}")
            st.page_link("pages/2_Resume.py", label="📄 简历管理")
            st.page_link("pages/3_QuestionBank.py", label="📚 题库管理")
            st.page_link("pages/4_Interview.py", label="💼 开始面试")
            st.page_link("pages/5_Report.py", label="📊 查看报告")
            st.page_link("pages/6_Admin.py", label="⚙️ 管理后台")
        else:
            st.page_link("pages/1_Auth.py", label="🔐 登录 / 注册")
        st.markdown("---")
        st.caption("AI 面试系统 v1.0")
    
    st.title("🎯 AI 面试系统")
    st.caption("基于 AI 的 Java 技术面试练习平台 · 支持简历解析、自适应出题、智能评分")
    st.markdown("---")
    
    if not st.session_state.authenticated:
        st.markdown("""
        <div class="welcome-banner">
            <h3 style="margin: 0 0 8px 0; color: white;">👋 欢迎使用 AI 面试系统</h3>
            <p style="margin: 0; opacity: 0.95;">登录或注册后即可使用简历管理、题库导入、模拟面试、智能评分等功能</p>
        </div>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.page_link("pages/1_Auth.py", label="🔐 前往登录 / 注册", icon="🔐")
    else:
        st.markdown(f"""
        <div class="welcome-banner">
            <h3 style="margin: 0 0 8px 0; color: white;">👋 欢迎回来，{st.session_state.user_email}</h3>
            <p style="margin: 0; opacity: 0.95;">选择下方功能开始你的面试之旅</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("### 功能导航")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.page_link("pages/2_Resume.py", label="📄 简历管理", icon="📄")
            st.page_link("pages/3_QuestionBank.py", label="📚 题库管理", icon="📚")
        
        with col2:
            st.page_link("pages/4_Interview.py", label="💼 开始面试", icon="💼")
            st.page_link("pages/5_Report.py", label="📊 查看报告", icon="📊")
        
        with col3:
            st.page_link("pages/6_Admin.py", label="⚙️ 管理后台", icon="⚙️")

if __name__ == "__main__":
    main()

