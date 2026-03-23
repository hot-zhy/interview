"""Bridge Streamlit Cloud Secrets to os.environ.

Must be imported BEFORE any backend module so that pydantic-settings
picks up DATABASE_URL etc. from Streamlit Cloud Secrets.
Safe to import multiple times (idempotent).
"""
import os

def bridge_secrets():
    try:
        import streamlit as st
        for key, value in st.secrets.items():
            if isinstance(value, str):
                os.environ.setdefault(key.upper(), value)
    except Exception:
        pass

bridge_secrets()
