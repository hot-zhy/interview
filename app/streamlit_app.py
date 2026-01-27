"""Streamlit main app."""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from app.components.auth_utils import init_session_state
from app.components.auth_loader import load_auth_on_page_load

# Page configuration
st.set_page_config(
    page_title="AI 面试系统",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load auth from localStorage first (before init_session_state)
load_auth_on_page_load()

# Initialize session state
init_session_state()

# Main app
def main():
    st.title("🎯 AI 面试系统")
    st.markdown("---")
    
    if not st.session_state.authenticated:
        st.info("请先登录或注册以使用系统功能。")
        st.page_link("pages/1_Auth.py", label="前往登录/注册页面", icon="🔐")
    else:
        st.success(f"欢迎，{st.session_state.user_email}！")
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

