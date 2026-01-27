"""Authentication utilities for Streamlit."""
import streamlit as st
from app.components.persist_auth import save_auth_to_storage, clear_auth_storage
from app.components.auth_loader import load_auth_on_page_load, check_and_restore_from_url


def init_session_state():
    """Initialize session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    
    # First, try to restore from URL params (set by JavaScript on previous run)
    if not st.session_state.authenticated:
        restored = check_and_restore_from_url()
        if restored:
            # Successfully restored, don't load script again
            return
    
    # If still not authenticated, try to load from localStorage via JavaScript
    if not st.session_state.authenticated:
        load_auth_on_page_load()


def check_auth():
    """Check if user is authenticated."""
    init_session_state()
    if not st.session_state.authenticated:
        st.error("请先登录")
        st.page_link("pages/1_Auth.py", label="前往登录页面", icon="🔐")
        st.stop()


def set_auth(user_id: int, user_email: str):
    """Set authentication state and persist to localStorage."""
    st.session_state.authenticated = True
    st.session_state.user_id = user_id
    st.session_state.user_email = user_email
    save_auth_to_storage(user_id, user_email)


def clear_auth():
    """Clear authentication state and localStorage."""
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.user_email = None
    clear_auth_storage()

