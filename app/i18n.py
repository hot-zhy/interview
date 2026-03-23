"""
Internationalization (i18n) for AI Interview System.
Supports Chinese (zh) and English (en).
"""
import streamlit as st

LANGUAGES = {"zh": "中文", "en": "English"}

TRANSLATIONS = {
    "zh": {
        "app": {
            "title": "AI 面试系统",
            "subtitle": "基于 AI 的 Java 技术面试练习平台 · 支持简历解析、自适应出题、智能评分",
            "nav": "快捷导航",
            "resume": "简历管理",
            "question_bank": "题库管理",
            "interview": "开始面试",
            "report": "查看报告",
            "admin": "管理后台",
            "login_register": "登录 / 注册",
            "version": "AI 面试系统 v1.0",
            "welcome": "欢迎使用 AI 面试系统",
            "welcome_desc": "登录或注册后即可使用简历管理、题库导入、模拟面试、智能评分等功能",
            "welcome_back": "欢迎回来",
            "welcome_back_desc": "选择下方功能开始你的面试之旅",
            "go_login": "前往登录 / 注册",
            "func_nav": "功能导航",
        },
        "auth": {
            "title": "登录 / 注册",
            "first_use": "首次使用请先注册账号",
            "login": "登录",
            "register": "注册",
            "login_tab": "登录",
            "register_tab": "注册",
            "login_header": "登录账号",
            "register_header": "创建新账号",
            "email": "邮箱",
            "password": "密码",
            "password_placeholder": "请输入密码",
            "password_confirm": "确认密码",
            "password_confirm_placeholder": "再次输入密码",
            "password_help": "密码长度 6-50 个字符",
            "password_min_placeholder": "至少 6 位字符",
            "submit_login": "登录",
            "submit_register": "注册",
            "fill_email_password": "请填写邮箱和密码",
            "password_mismatch": "两次输入的密码不一致",
            "password_too_short": "密码长度至少 6 位",
            "password_too_long": "密码过长（最多 50 个字符）",
            "password_bytes_long": "密码过长（最多 72 字节）",
            "email_registered": "该邮箱已被注册",
            "user_not_found": "用户不存在",
            "wrong_password": "密码错误",
            "register_success": "注册成功！",
            "login_success": "登录成功！",
            "switch_to_login": "请切换到「登录」标签页登录",
            "logged_in": "已登录",
            "logout": "退出登录",
            "logout_success": "已退出登录",
        },
        "common": {
            "login_required": "请先登录以使用此功能",
            "go_login": "前往登录 / 注册",
        },
        "interview": {
            "title": "开始面试",
            "subtitle": "选择技术方向、难度和轮数，支持文字或语音回答",
            "create_new": "创建新面试",
            "track": "技术方向",
            "initial_level": "初始难度",
            "rounds": "面试轮数",
            "use_resume": "基于简历定制题目",
            "select_resume": "选择简历",
            "upload_resume_first": "请先上传简历",
            "resume_track_mismatch": "简历与所选岗位方向不匹配，请更换简历或选择其他岗位方向",
            "start_interview": "开始面试",
            "session_created": "面试已创建！",
            "interviewer": "面试官",
            "chat_area": "对话区",
            "input_answer": "输入回答",
            "text_answer": "文字回答",
            "voice_answer": "语音回答",
            "answer_placeholder": "在此输入你的回答...",
            "submit": "提交回答",
            "end_interview": "结束面试",
            "exit_session": "退出当前面试",
            "session_info": "面试信息",
            "direction": "方向",
            "difficulty": "难度",
            "status": "状态",
            "rounds_count": "轮数",
            "start_first": "开始第一题",
            "preparing": "正在准备题目...",
            "session_not_found": "面试会话不存在",
            "interview_progress": "面试进行中",
            "round": "轮",
            "please_input": "请先输入回答",
            "submitting": "正在提交并评价...",
            "submitting_audio": "正在提交并分析语音回答...",
            "audio_tip": "点击下方录音按钮，录完后将自动提交；分析在后台进行，面试结束后可在报告中查看结果。",
            "audio_too_short": "录音太短，请录制至少约 1 秒后再提交。",
            "use_recorder": "请使用上方录音组件录完音（将自动提交），或在此上传录音文件",
            "upload_audio": "上传录音文件",
            "interview_ended": "面试已结束，请查看报告页面",
            "expression_video": "实时表情",
            "expression_caption": "实时表情分析（后台自动记录，面试结束后写入报告）",
            "expression_samples": "已采集 {n} 次表情样本",
        },
        "resume": {
            "title": "简历管理",
            "subtitle": "上传 PDF 或 DOCX 简历，系统将自动解析教育背景、工作经历、技能等信息",
            "upload": "上传简历",
            "select_file": "选择 PDF 或 DOCX 文件",
            "file_help": "支持 PDF 和 DOCX 格式，最大 200MB",
            "file_selected": "已选择文件",
            "parse_save": "解析并保存",
            "parsing": "正在解析简历...",
            "success": "简历上传并解析成功！",
            "parse_failed": "解析失败",
        },
        "question_bank": {
            "title": "题库管理",
            "subtitle": "导入 Excel 题库，支持按章节、难度分类",
        },
        "report": {
            "title": "面试报告",
            "subtitle": "查看面试评分、优势短板、缺失知识点与学习建议",
            "no_sessions": "暂无完成的面试，请先在「开始面试」页面完成一次面试",
            "select_session": "选择面试",
            "generate": "生成报告",
            "generating": "正在生成报告...",
            "generate_success": "报告生成成功！",
        },
        "expression_video": {
            "install_hint": "实时表情分析需要安装 streamlit-webrtc，请运行: pip install streamlit-webrtc",
        },
    },
    "en": {
        "app": {
            "title": "AI Interview System",
            "subtitle": "AI-powered Java technical interview practice · Resume parsing, adaptive questions, smart scoring",
            "nav": "Quick Nav",
            "resume": "Resume",
            "question_bank": "Question Bank",
            "interview": "Interview",
            "report": "Reports",
            "admin": "Admin",
            "login_register": "Login / Register",
            "version": "AI Interview System v1.0",
            "welcome": "Welcome to AI Interview System",
            "welcome_desc": "Log in or register to use resume management, question bank, mock interviews, and smart scoring",
            "welcome_back": "Welcome back",
            "welcome_back_desc": "Choose a feature below to start your interview journey",
            "go_login": "Go to Login / Register",
            "func_nav": "Features",
        },
        "auth": {
            "title": "Login / Register",
            "first_use": "Register first if this is your first visit",
            "login": "Login",
            "register": "Register",
            "login_tab": "Login",
            "register_tab": "Register",
            "login_header": "Login",
            "register_header": "Create Account",
            "email": "Email",
            "password": "Password",
            "password_placeholder": "Enter password",
            "password_confirm": "Confirm Password",
            "password_confirm_placeholder": "Re-enter password",
            "password_help": "6-50 characters",
            "password_min_placeholder": "At least 6 characters",
            "submit_login": "Login",
            "submit_register": "Register",
            "fill_email_password": "Please enter email and password",
            "password_mismatch": "Passwords do not match",
            "password_too_short": "Password must be at least 6 characters",
            "password_too_long": "Password too long (max 50 characters)",
            "password_bytes_long": "Password too long (max 72 bytes)",
            "email_registered": "Email already registered",
            "user_not_found": "User not found",
            "wrong_password": "Wrong password",
            "register_success": "Registration successful!",
            "login_success": "Login successful!",
            "switch_to_login": "Please switch to the Login tab to sign in",
            "logged_in": "Logged in",
            "logout": "Logout",
            "logout_success": "Logged out",
        },
        "common": {
            "login_required": "Please log in to use this feature",
            "go_login": "Go to Login / Register",
        },
        "interview": {
            "title": "Start Interview",
            "subtitle": "Choose track, difficulty, and rounds. Supports text or voice answers.",
            "create_new": "Create New Interview",
            "track": "Track",
            "initial_level": "Initial Difficulty",
            "rounds": "Rounds",
            "use_resume": "Customize questions by resume",
            "select_resume": "Select Resume",
            "upload_resume_first": "Please upload a resume first",
            "resume_track_mismatch": "Resume does not match the selected job track. Please use a different resume or choose another track.",
            "start_interview": "Start Interview",
            "session_created": "Interview created!",
            "interviewer": "Interviewer",
            "chat_area": "Chat",
            "input_answer": "Your Answer",
            "text_answer": "Text",
            "voice_answer": "Voice",
            "answer_placeholder": "Type your answer here...",
            "submit": "Submit",
            "end_interview": "End Interview",
            "exit_session": "Exit Session",
            "session_info": "Session Info",
            "direction": "Track",
            "difficulty": "Difficulty",
            "status": "Status",
            "rounds_count": "Rounds",
            "start_first": "Start First Question",
            "preparing": "Preparing...",
            "session_not_found": "Session not found",
            "interview_progress": "Interview in Progress",
            "round": "Round",
            "please_input": "Please enter your answer",
            "submitting": "Submitting...",
            "submitting_audio": "Submitting and analyzing...",
            "audio_tip": "Click record, then submit. Results appear in the report after the interview.",
            "audio_too_short": "Recording too short. Please record at least ~1 second.",
            "use_recorder": "Use the recorder above or upload an audio file",
            "upload_audio": "Upload Audio",
            "interview_ended": "Interview ended. View the report.",
            "expression_video": "Expression",
            "expression_caption": "Real-time expression analysis (saved to report)",
            "expression_samples": "{n} expression samples collected",
        },
        "resume": {
            "title": "Resume",
            "subtitle": "Upload PDF or DOCX. We parse education, experience, and skills.",
            "upload": "Upload Resume",
            "select_file": "Select PDF or DOCX",
            "file_help": "PDF and DOCX, max 200MB",
            "file_selected": "Selected",
            "parse_save": "Parse & Save",
            "parsing": "Parsing...",
            "success": "Resume uploaded and parsed!",
            "parse_failed": "Parse failed",
        },
        "question_bank": {
            "title": "Question Bank",
            "subtitle": "Import Excel question bank with chapters and difficulty levels",
        },
        "report": {
            "title": "Interview Report",
            "subtitle": "View scores, strengths, weaknesses, and learning suggestions",
            "no_sessions": "No completed interviews. Complete one first.",
            "select_session": "Select Interview",
            "generate": "Generate Report",
            "generating": "Generating...",
            "generate_success": "Report generated!",
        },
        "expression_video": {
            "install_hint": "Install streamlit-webrtc: pip install streamlit-webrtc",
        },
    },
}


def get_lang() -> str:
    """Get current language from session state."""
    if "lang" not in st.session_state:
        st.session_state.lang = "zh"
    return st.session_state.lang


def set_lang(lang: str):
    """Set language and trigger rerun."""
    if lang in LANGUAGES:
        st.session_state.lang = lang


def t(key: str, **kwargs) -> str:
    """
    Get translated string. Key format: "section.key" e.g. "auth.title"
    Supports format: t("msg", count=5) for "Collected {} samples" -> "Collected 5 samples"
    """
    lang = get_lang()
    trans = TRANSLATIONS.get(lang, TRANSLATIONS["zh"])
    keys = key.split(".")
    obj = trans
    for k in keys:
        obj = obj.get(k, key)
        if isinstance(obj, str):
            break
    if isinstance(obj, str) and kwargs:
        return obj.format(**kwargs)
    return obj if isinstance(obj, str) else key
