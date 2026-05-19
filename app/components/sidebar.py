"""Shared sidebar with navigation and language switcher."""
import streamlit as st
from app.i18n import t, get_lang, set_lang


def render_sidebar():
    """Render the shared sidebar (nav + language switcher). Call from each page."""
    with st.sidebar:
        st.markdown(
            """
            <div style="
                border:1px solid rgba(125,211,252,0.22);
                border-radius:8px;
                padding:14px 14px 12px;
                background:rgba(255,255,255,0.07);
                box-shadow:0 16px 40px rgba(0,0,0,0.18);
                margin-bottom:16px;
            ">
                <div style="font-size:0.72rem;color:rgba(203,213,225,0.78);font-weight:700;">AI INTERVIEW OS</div>
                <div style="font-size:1.05rem;color:#fff;font-weight:780;margin-top:4px;">智能面试工作台</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
        st.caption("Language / 语言")
        st.markdown("---")
        if st.session_state.get("authenticated"):
            st.markdown(
                f"""
                <div style="
                    border:1px solid rgba(148,163,184,0.18);
                    border-radius:8px;
                    padding:10px 12px;
                    background:rgba(15,23,42,0.28);
                    margin-bottom:10px;
                    font-size:0.82rem;
                    color:rgba(226,232,240,0.9);
                    word-break:break-word;
                ">{st.session_state.user_email}</div>
                """,
                unsafe_allow_html=True,
            )
            st.page_link("pages/2_Resume.py", label=t('app.resume'))
            st.page_link("pages/3_QuestionBank.py", label=t('app.question_bank'))
            st.page_link("pages/4_Interview.py", label=t('app.interview'))
            st.page_link("pages/5_Report.py", label=t('app.report'))
            st.page_link("pages/6_Admin.py", label=t('app.admin'))
        else:
            st.page_link("pages/1_Auth.py", label=t('app.login_register'))
        st.markdown("---")
        st.caption(t("app.version"))
