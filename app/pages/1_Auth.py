"""Authentication page."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
from sqlalchemy.orm import Session
from backend.db.base import get_db
from backend.db.models import User
from backend.core.security import verify_password, get_password_hash
from backend.core.logging import logger
from app.components.auth_utils import init_session_state
from app.components.auth_loader import load_auth_on_page_load
from app.components.styles import inject_global_styles
from app.components.sidebar import render_sidebar
from app.i18n import t

st.set_page_config(page_title="Login/Register", page_icon="🔐")

# Inject global styles
inject_global_styles()

# Load auth from localStorage first
load_auth_on_page_load()

# Initialize session state
init_session_state()

def register_user(db: Session, email: str, password: str) -> tuple[bool, str]:
    """Register a new user."""
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return False, t("auth.email_registered")
    
    # Create new user
    try:
        new_user = User(
            email=email,
            password_hash=get_password_hash(password)
        )
        db.add(new_user)
        db.commit()
        return True, t("auth.register_success")
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        return False, f"{t('resume.parse_failed')}: {str(e)}"


def login_user(db: Session, email: str, password: str) -> tuple[bool, str, int]:
    """Login user."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False, t("auth.user_not_found"), None
    if not verify_password(password, user.password_hash):
        return False, t("auth.wrong_password"), None
    return True, t("auth.login_success"), user.id


def main():
    render_sidebar()
    st.title(f"🔐 {t('auth.title')}")
    st.caption(t("auth.first_use"))
    st.markdown("---")
    
    col_left, col_center, col_right = st.columns([1, 2, 1])
    
    with col_center:
        tab1, tab2 = st.tabs([f"📥 {t('auth.login_tab')}", f"📝 {t('auth.register_tab')}"])
        
        with tab1:
            st.subheader(t("auth.login_header"))
            with st.form("login_form"):
                email = st.text_input(t("auth.email"), key="login_email", placeholder="your@email.com")
                password = st.text_input(t("auth.password"), type="password", key="login_password", placeholder=t("auth.password_placeholder"))
                submit = st.form_submit_button(t("auth.submit_login"), use_container_width=True, type="primary")
                
                if submit:
                    if not email or not password:
                        st.error(t("auth.fill_email_password"))
                    else:
                        db = next(get_db())
                        success, message, user_id = login_user(db, email, password)
                        if success:
                            from app.components.auth_utils import set_auth
                            set_auth(user_id, email)
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
        
        with tab2:
            st.subheader(t("auth.register_header"))
            with st.form("register_form"):
                email = st.text_input(t("auth.email"), key="register_email", placeholder="your@email.com")
                password = st.text_input(
                    t("auth.password"), 
                    type="password", 
                    key="register_password",
                    placeholder=t("auth.password_min_placeholder"),
                    help=t("auth.password_help")
                )
                password_confirm = st.text_input(t("auth.password_confirm"), type="password", key="register_password_confirm", placeholder=t("auth.password_confirm_placeholder"))
                submit = st.form_submit_button(t("auth.submit_register"), use_container_width=True, type="primary")
                
                if submit:
                    if not email or not password:
                        st.error(t("auth.fill_email_password"))
                    elif password != password_confirm:
                        st.error(t("auth.password_mismatch"))
                    elif len(password) < 6:
                        st.error(t("auth.password_too_short"))
                    elif len(password) > 50:
                        st.error(t("auth.password_too_long"))
                    elif len(password.encode('utf-8')) > 72:
                        st.error(t("auth.password_bytes_long"))
                    else:
                        db = next(get_db())
                        success, message = register_user(db, email, password)
                        if success:
                            st.success(message)
                            st.info(t("auth.switch_to_login"))
                        else:
                            st.error(message)
    
    if st.session_state.authenticated:
        with col_center:
            st.markdown("---")
            st.success(f"{t('auth.logged_in')}：{st.session_state.user_email}")
            if st.button(t("auth.logout"), use_container_width=True, type="secondary"):
                from app.components.auth_utils import clear_auth
                clear_auth()
                st.success(t("auth.logout_success"))
                st.rerun()

if __name__ == "__main__":
    main()

