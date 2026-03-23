"""Bridge Streamlit Cloud Secrets to os.environ and auto-init database.

Must be imported BEFORE any backend module so that pydantic-settings
picks up DATABASE_URL etc. from Streamlit Cloud Secrets.
Safe to import multiple times (idempotent).
"""
import os

_BRIDGED = False

def bridge_secrets():
    global _BRIDGED
    if _BRIDGED:
        return
    _BRIDGED = True

    # 1. Copy Streamlit Cloud Secrets into environment variables
    try:
        import streamlit as st
        for key, value in st.secrets.items():
            if isinstance(value, str):
                os.environ.setdefault(key.upper(), value)
    except Exception:
        pass

    # 2. Auto-create database tables (idempotent, runs once per process)
    try:
        from backend.db.base import Base, engine
        from backend.db import models  # noqa: register all models
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[secrets_bridge] auto_init_db: {e}")

bridge_secrets()
