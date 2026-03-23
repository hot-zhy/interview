"""Shared sidebar with navigation and language switcher."""
import streamlit as st
from app.i18n import t, get_lang, set_lang


def render_sidebar():
    """Render the shared sidebar (nav + language switcher). Call from each page."""
    with st.sidebar:
        st.markdown(f"### {t('app.nav')}")
        lang = get_lang()
        lang_cols = st.columns(2)
        with lang_cols[0]:
            if st.button("中文", key="lang_zh", use_container_width=True, type="primary" if lang == "zh" else "secondary"):
                set_lang("zh")
                st.rerun()
        with lang_cols[1]:
            if st.button("EN", key="lang_en", use_container_width=True, type="primary" if lang == "en" else "secondary"):
                set_lang("en")
                st.rerun()
        st.caption("Language")
        st.markdown("---")
        if st.session_state.get("authenticated"):
            st.caption(st.session_state.user_email)
            st.page_link("pages/2_Resume.py", label=t('app.resume'))
            st.page_link("pages/3_QuestionBank.py", label=t('app.question_bank'))
            st.page_link("pages/4_Interview.py", label=t('app.interview'))
            st.page_link("pages/5_Report.py", label=t('app.report'))
            st.page_link("pages/6_Admin.py", label=t('app.admin'))
        else:
            st.page_link("pages/1_Auth.py", label=t('app.login_register'))
        st.markdown("---")
        st.caption(t("app.version"))
