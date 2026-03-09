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
from app.i18n import t, get_lang, set_lang
from app.components.sidebar import render_sidebar

# Page configuration
st.set_page_config(
    page_title="AI Interview System",
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
    render_sidebar()
    st.title(f"🎯 {t('app.title')}")
    st.caption(t("app.subtitle"))
    st.markdown("---")
    
    if not st.session_state.authenticated:
        st.markdown(f"""
        <div class="welcome-banner">
            <h3 style="margin: 0 0 8px 0; color: white;">👋 {t('app.welcome')}</h3>
            <p style="margin: 0; opacity: 0.95;">{t('app.welcome_desc')}</p>
        </div>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.page_link("pages/1_Auth.py", label=f"🔐 {t('app.go_login')}", icon="🔐")
    else:
        st.markdown(f"""
        <div class="welcome-banner">
            <h3 style="margin: 0 0 8px 0; color: white;">👋 {t('app.welcome_back')}，{st.session_state.user_email}</h3>
            <p style="margin: 0; opacity: 0.95;">{t('app.welcome_back_desc')}</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"### {t('app.func_nav')}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.page_link("pages/2_Resume.py", label=f"📄 {t('app.resume')}", icon="📄")
            st.page_link("pages/3_QuestionBank.py", label=f"📚 {t('app.question_bank')}", icon="📚")
        
        with col2:
            st.page_link("pages/4_Interview.py", label=f"💼 {t('app.interview')}", icon="💼")
            st.page_link("pages/5_Report.py", label=f"📊 {t('app.report')}", icon="📊")
        
        with col3:
            st.page_link("pages/6_Admin.py", label=f"⚙️ {t('app.admin')}", icon="⚙️")

if __name__ == "__main__":
    main()

