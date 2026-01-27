# 项目结构说明

## 目录结构

```
AIIntegerviewer/
├── app/                          # Streamlit 应用
│   ├── streamlit_app.py         # 主入口
│   ├── pages/                   # 多页面应用
│   │   ├── 1_Auth.py           # 登录/注册
│   │   ├── 2_Resume.py         # 简历管理
│   │   ├── 3_QuestionBank.py   # 题库管理
│   │   ├── 4_Interview.py      # 面试房间
│   │   ├── 5_Report.py         # 报告查看
│   │   └── 6_Admin.py          # 管理后台
│   └── components/              # UI 组件
│       ├── avatar.py           # 数字人 Avatar
│       ├── tts.py              # TTS 组件
│       └── ui.py               # 通用 UI
│
├── backend/                      # 后端逻辑
│   ├── core/                    # 核心配置
│   │   ├── config.py           # 应用配置
│   │   ├── security.py         # 安全工具（密码、JWT）
│   │   └── logging.py          # 日志配置
│   ├── db/                      # 数据库
│   │   ├── base.py             # 数据库基础
│   │   ├── session.py          # 会话管理
│   │   ├── models.py           # 数据模型
│   │   └── migrations/         # Alembic 迁移
│   ├── schemas/                 # Pydantic schemas
│   │   ├── auth.py
│   │   ├── resume.py
│   │   ├── question.py
│   │   ├── interview.py
│   │   ├── evaluation.py
│   │   └── report.py
│   └── services/                # 业务逻辑
│       ├── resume_parser.py    # 简历解析
│       ├── question_bank_loader.py  # 题库导入
│       ├── question_selector.py    # 抽题策略
│       ├── evaluator_rules.py      # 规则评分
│       ├── llm_provider.py         # LLM 评分（可选）
│       ├── interview_engine.py     # 面试引擎
│       └── report_generator.py     # 报告生成
│
├── data/                         # 数据目录
│   ├── README.md                # 数据说明
│   └── interview.db             # SQLite 数据库（运行后生成）
│
├── tests/                        # 测试用例
│   ├── test_import_questions.py
│   ├── test_interview_flow.py
│   └── test_eval_rules.py
│
├── scripts/                      # 工具脚本
│   └── init_db.py              # 数据库初始化
│
├── alembic.ini                   # Alembic 配置
├── requirements.txt              # Python 依赖
├── .env.example                 # 环境变量示例
├── .gitignore                   # Git 忽略文件
├── README.md                    # 项目说明
├── QUICKSTART.md                # 快速开始
└── run.py                       # 快速启动脚本
```

## 核心模块说明

### 1. 认证模块 (`app/pages/1_Auth.py`)
- 用户注册/登录
- 密码加密存储（bcrypt）
- Session 状态管理

### 2. 简历模块 (`app/pages/2_Resume.py`)
- 支持 PDF/DOCX 上传
- 自动解析为结构化信息
- 支持手动编辑

### 3. 题库模块 (`app/pages/3_QuestionBank.py`)
- Excel 题库导入
- 增量更新（upsert）
- 按章节/难度筛选

### 4. 面试模块 (`app/pages/4_Interview.py`)
- 创建面试会话
- 自适应出题
- 实时评价反馈
- 数字人 Avatar + TTS

### 5. 报告模块 (`app/pages/5_Report.py`)
- 生成面试报告
- 分项评分展示
- 学习建议推荐

### 6. 管理后台 (`app/pages/6_Admin.py`)
- 系统统计
- 面试记录查看
- 题库统计

## 数据模型

### User
- 用户基本信息
- 密码哈希

### Resume
- 简历原始文本
- 解析后的结构化 JSON

### QuestionBank
- 题目库
- 支持按 ID upsert

### InterviewSession
- 面试会话
- 状态管理

### InterviewTurn
- 对话记录
- 面试官/候选人消息

### AskedQuestion
- 已问题目记录
- 关联题库题目

### Evaluation
- 评价结果
- 分项评分
- 缺失知识点

### Report
- 面试报告
- Markdown 格式

## 技术栈

- **UI**: Streamlit
- **数据库**: SQLite + SQLAlchemy 2.x
- **ORM**: Alembic（迁移管理）
- **安全**: passlib (bcrypt) + python-jose (JWT)
- **文本处理**: rapidfuzz（相似度计算）
- **简历解析**: pdfplumber + python-docx
- **配置**: pydantic-settings
- **测试**: pytest

## 关键特性

1. **无 LLM 模式**：系统可以在没有 LLM API Key 的情况下运行
2. **规则评分**：基于关键词覆盖和相似度的确定性评分
3. **自适应出题**：根据答题表现动态调整难度
4. **数字人交互**：2D Avatar + Web Speech API TTS
5. **完整报告**：自动生成包含学习建议的详细报告

