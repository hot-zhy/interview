"""Authentication page."""
import streamlit as st
from sqlalchemy.orm import Session
from backend.db.base import get_db
from backend.db.models import User
from backend.core.security import verify_password, get_password_hash
from backend.core.logging import logger
from app.components.auth_utils import init_session_state
from app.components.auth_loader import load_auth_on_page_load
from app.components.styles import inject_global_styles

st.set_page_config(page_title="登录/注册", page_icon="🔐")

# Inject global styles
inject_global_styles()

# Load auth from localStorage first
load_auth_on_page_load()

# Initialize session state
init_session_state()

def register_user(db: Session, email: str, password: str) -> tuple[bool, str]:
    """Register a new user."""
    # Check if user exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return False, "该邮箱已被注册"
    
    # Create new user
    try:
        new_user = User(
            email=email,
            password_hash=get_password_hash(password)
        )
        db.add(new_user)
        db.commit()
        return True, "注册成功！"
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        return False, f"注册失败：{str(e)}"


def login_user(db: Session, email: str, password: str) -> tuple[bool, str, int]:
    """Login user."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False, "用户不存在", None
    
    if not verify_password(password, user.password_hash):
        return False, "密码错误", None
    
    return True, "登录成功！", user.id


def main():
    st.title("🔐 登录 / 注册")
    st.caption("首次使用请先注册账号")
    st.markdown("---")
    
    # 居中布局：使用列实现表单居中
    col_left, col_center, col_right = st.columns([1, 2, 1])
    
    with col_center:
        tab1, tab2 = st.tabs(["📥 登录", "📝 注册"])
        
        with tab1:
            st.subheader("登录账号")
            with st.form("login_form"):
                email = st.text_input("邮箱", key="login_email", placeholder="your@email.com")
                password = st.text_input("密码", type="password", key="login_password", placeholder="请输入密码")
                submit = st.form_submit_button("登录", use_container_width=True, type="primary")
                
                if submit:
                    if not email or not password:
                        st.error("请填写邮箱和密码")
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
            st.subheader("创建新账号")
            with st.form("register_form"):
                email = st.text_input("邮箱", key="register_email", placeholder="your@email.com")
                password = st.text_input(
                    "密码", 
                    type="password", 
                    key="register_password",
                    placeholder="至少 6 位字符",
                    help="密码长度 6-50 个字符"
                )
                password_confirm = st.text_input("确认密码", type="password", key="register_password_confirm", placeholder="再次输入密码")
                submit = st.form_submit_button("注册", use_container_width=True, type="primary")
                
                if submit:
                    if not email or not password:
                        st.error("请填写邮箱和密码")
                    elif password != password_confirm:
                        st.error("两次输入的密码不一致")
                    elif len(password) < 6:
                        st.error("密码长度至少 6 位")
                    elif len(password) > 50:
                        st.error("密码过长（最多 50 个字符）")
                    elif len(password.encode('utf-8')) > 72:
                        st.error("密码过长（最多 72 字节）")
                    else:
                        db = next(get_db())
                        success, message = register_user(db, email, password)
                        if success:
                            st.success(message)
                            st.info('请切换到「登录」标签页登录')
                        else:
                            st.error(message)
    
    if st.session_state.authenticated:
        with col_center:
            st.markdown("---")
            st.success(f"已登录：{st.session_state.user_email}")
            if st.button("退出登录", use_container_width=True, type="secondary"):
                from app.components.auth_utils import clear_auth
                clear_auth()
                st.success("已退出登录")
                st.rerun()

if __name__ == "__main__":
    main()

