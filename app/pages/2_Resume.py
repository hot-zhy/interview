"""Resume management page."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.components.secrets_bridge import bridge_secrets; bridge_secrets()

import streamlit as st
import os
import tempfile
from sqlalchemy.orm import Session
from backend.db.base import get_db
from backend.db.models import Resume
from backend.services.resume_parser import parse_resume
from backend.core.logging import logger
from app.components.auth_utils import init_session_state, check_auth
from app.components.auth_loader import load_auth_on_page_load
from app.components.styles import inject_global_styles
from app.components.sidebar import render_sidebar
from app.i18n import t
import json

st.set_page_config(page_title="Resume", layout="wide")

# Inject global styles
inject_global_styles()

# Load auth from localStorage first
load_auth_on_page_load()

# Initialize session state
init_session_state()

def main():
    render_sidebar()
    check_auth()
    
    st.title(t('resume.title'))
    st.caption(t("resume.subtitle"))
    st.markdown("---")
    
    user_id = st.session_state.user_id
    db = next(get_db())
    
    resumes = db.query(Resume).filter(Resume.user_id == user_id).order_by(Resume.created_at.desc()).all()
    
    st.subheader(t('resume.upload'))
    uploaded_file = st.file_uploader(
        t("resume.select_file"),
        type=["pdf", "docx", "doc", "png", "jpg", "jpeg", "bmp", "tiff", "webp"],
        help="支持 PDF、DOCX、图片（PNG/JPG/BMP/TIFF/WebP）格式"
    )
    
    if uploaded_file is not None:
        size_kb = getattr(uploaded_file, 'size', 0) / 1024
        st.info(f"{t('resume.file_selected')}: **{uploaded_file.name}** ({size_kb:.1f} KB)")
        if st.button(t("resume.parse_save"), use_container_width=True, type="primary"):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                with st.spinner(t("resume.parsing")):
                    parsed_data = parse_resume(tmp_path, uploaded_file.name)
                
                resume = Resume(
                    user_id=user_id,
                    filename=uploaded_file.name,
                    raw_text=parsed_data.get("raw_text", ""),
                    parsed_json=parsed_data
                )
                db.add(resume)
                db.commit()
                db.refresh(resume)
                
                os.unlink(tmp_path)
                
                st.success(t("resume.success"))
                st.rerun()
                
            except Exception as e:
                logger.error(f"Resume parsing error: {e}")
                st.error(f"{t('resume.parse_failed')}: {str(e)}")
                if 'tmp_path' in locals():
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
    
    st.markdown("---")
    
    # Display resumes
    st.subheader("我的简历")
    
    if not resumes:
        st.info("暂无简历，请在上方上传一份 PDF 或 DOCX 格式的简历")
    else:
        for resume in resumes:
            with st.expander(f"{resume.filename} · 上传于 {resume.created_at.strftime('%Y-%m-%d %H:%M')}", expanded=False):
                # Display parsed data
                if resume.parsed_json:
                    parsed = resume.parsed_json
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### 教育背景")
                        if parsed.get("education"):
                            for edu in parsed["education"]:
                                st.text(edu)
                        else:
                            st.text("未识别")
                        
                        st.markdown("#### 工作经历")
                        if parsed.get("experience"):
                            for exp in parsed["experience"]:
                                st.text(exp)
                        else:
                            st.text("未识别")
                    
                    with col2:
                        st.markdown("#### 项目经历")
                        if parsed.get("projects"):
                            for proj in parsed["projects"]:
                                st.text(proj)
                        else:
                            st.text("未识别")
                        
                        st.markdown("#### 技能")
                        if parsed.get("skills"):
                            st.write(", ".join(parsed["skills"]))
                        else:
                            st.text("未识别")
                    
                    # Edit parsed data
                    st.markdown("---")
                    st.markdown("#### 编辑解析结果")
                    
                    edited_json = st.text_area(
                        "编辑 JSON 数据",
                        value=json.dumps(parsed, ensure_ascii=False, indent=2),
                        height=300,
                        key=f"edit_{resume.id}"
                    )
                    
                    if st.button("保存修改", key=f"save_{resume.id}"):
                        try:
                            edited_data = json.loads(edited_json)
                            resume.parsed_json = edited_data
                            db.commit()
                            st.success("修改已保存")
                            st.rerun()
                        except json.JSONDecodeError:
                            st.error("JSON 格式错误")
                        except Exception as e:
                            st.error(f"保存失败：{str(e)}")
                else:
                    st.info("该简历尚未解析")
                
                # Delete button
                if st.button("删除简历", key=f"delete_{resume.id}", type="secondary"):
                    db.delete(resume)
                    db.commit()
                    st.success("已删除")
                    st.rerun()

if __name__ == "__main__":
    main()

