"""Question bank management page."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import os
import tempfile
from sqlalchemy.orm import Session
from backend.db.base import get_db
from backend.db.models import QuestionBank
from backend.services.question_bank_loader import import_questions_from_excel
from backend.core.logging import logger
from app.components.auth_utils import init_session_state, check_auth
from app.components.auth_loader import load_auth_on_page_load
from app.components.styles import inject_global_styles
from app.components.sidebar import render_sidebar
from app.i18n import t

st.set_page_config(page_title="Question Bank", layout="wide")

# Inject global styles
inject_global_styles()

# Load auth from localStorage first
load_auth_on_page_load()

# Initialize session state
init_session_state()

def main():
    render_sidebar()
    check_auth()
    
    st.title(t('question_bank.title'))
    st.caption(t("question_bank.subtitle"))
    st.markdown("---")
    
    with st.spinner(t("common.loading")):
        db = next(get_db())
    
    # Load from fixed file path
    st.subheader("题库加载")
    
    # Fixed file path
    question_file_path = "data/question.xlsx"
    file_exists = os.path.exists(question_file_path)
    
    if file_exists:
        st.success(f"找到题库文件: `{question_file_path}`")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("点击下方按钮从固定题库文件加载题目到数据库")
        with col2:
            if st.button("加载题库", use_container_width=True, type="primary"):
                try:
                    # Close current session and create a new one for import
                    db.close()
                    db = next(get_db())
                    
                    # Import questions from fixed file
                    with st.spinner("正在从题库文件导入..."):
                        result = import_questions_from_excel(db, question_file_path)
                    
                    # Display results
                    st.success("导入完成！")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("总计", result.total)
                    col2.metric("新增", result.created, delta=f"+{result.created}" if result.created > 0 else None)
                    col3.metric("更新", result.updated, delta=f"+{result.updated}" if result.updated > 0 else None)
                    col4.metric("失败", result.failed, delta=f"-{result.failed}" if result.failed > 0 else None)
                    
                    if result.skipped > 0:
                        st.warning(f"跳过 {result.skipped} 条记录（数据不完整）")
                    
                    if result.errors:
                        with st.expander("查看错误详情"):
                            for error in result.errors[:20]:  # Show first 20 errors
                                st.text(error)
                    
                    # Verify import - create a fresh session to check count
                    db.close()
                    verify_db = next(get_db())
                    verify_count = verify_db.query(QuestionBank).count()
                    verify_db.close()
                    
                    if verify_count > 0:
                        st.success(f"验证成功：当前数据库中的题目总数: {verify_count}")
                    else:
                        st.warning("警告：导入报告成功，但数据库中题目数为 0。请检查导入结果。")
                        if result.created == 0 and result.updated == 0:
                            st.error("没有题目被创建或更新，请检查 Excel 文件格式和内容。")
                    
                    st.rerun()
                    
                except Exception as e:
                    logger.error(f"Import error: {e}")
                    st.error(f"导入失败：{str(e)}")
                    import traceback
                    with st.expander("查看详细错误"):
                        st.code(traceback.format_exc())
                finally:
                    # Ensure db is closed
                    try:
                        db.close()
                    except:
                        pass
    else:
        st.warning(f"题库文件不存在: `{question_file_path}`")
        st.info("""
        **请按以下步骤操作：**
        1. 在项目根目录创建 `data` 文件夹（如果不存在）
        2. 将你的题库 Excel 文件命名为 `question.xlsx` 并放入 `data` 文件夹
        3. 确保 Excel 文件包含以下表头：`id`, `question`, `correct_answer`, `difficulty`, `chapter`
        4. 刷新此页面，然后点击"加载题库"按钮
        """)
        
        # Show current directory structure
        with st.expander("查看当前目录结构"):
            if os.path.exists("data"):
                st.text("data/ 目录存在")
                files = os.listdir("data")
                if files:
                    st.text("data/ 目录中的文件：")
                    for f in files:
                        st.text(f"  - {f}")
                else:
                    st.text("data/ 目录为空")
            else:
                st.text("data/ 目录不存在")
    
    st.markdown("---")
    
    # Statistics
    st.subheader("题库统计")
    
    # Create a fresh session to ensure we see latest data
    try:
        db.close()
    except:
        pass
    db = next(get_db())
    total_count = db.query(QuestionBank).count()
    st.metric("总题目数", total_count)
    
    if total_count > 0:
        # Statistics by chapter
        chapters = db.query(QuestionBank.chapter).distinct().all()
        st.markdown("#### 按章节统计")
        
        chapter_stats = {}
        for (chapter,) in chapters:
            count = db.query(QuestionBank).filter(QuestionBank.chapter == chapter).count()
            chapter_stats[chapter] = count
        
        for chapter, count in sorted(chapter_stats.items(), key=lambda x: x[1], reverse=True):
            st.text(f"{chapter}: {count} 题")
        
        # Statistics by difficulty
        st.markdown("#### 按难度统计")
        difficulty_stats = {}
        for diff in range(1, 6):
            count = db.query(QuestionBank).filter(QuestionBank.difficulty == diff).count()
            if count > 0:
                difficulty_stats[diff] = count
        
        for diff, count in sorted(difficulty_stats.items()):
            st.text(f"难度 {diff}: {count} 题")
        
        # Browse questions
        st.markdown("---")
        st.subheader("浏览题目")
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            selected_chapter = st.selectbox(
                "按章节筛选",
                options=["全部"] + [c[0] for c in chapters],
                key="filter_chapter"
            )
        with col2:
            selected_difficulty = st.selectbox(
                "按难度筛选",
                options=["全部"] + list(range(1, 6)),
                key="filter_difficulty"
            )
        
        # Query questions
        query = db.query(QuestionBank)
        if selected_chapter != "全部":
            query = query.filter(QuestionBank.chapter == selected_chapter)
        if selected_difficulty != "全部":
            query = query.filter(QuestionBank.difficulty == selected_difficulty)
        
        questions = query.limit(50).all()
        
        st.markdown(f"显示 {len(questions)} 题（最多50题）")
        
        for q in questions:
            with st.expander(f"题目 {q.id} - {q.chapter} (难度: {q.difficulty})"):
                st.markdown(f"**题目**: {q.question}")
                st.markdown(f"**标准答案**: {q.correct_answer}")
                st.caption(f"创建时间: {q.created_at}")
    else:
        st.info("题库为空，请先导入题目")

if __name__ == "__main__":
    main()

