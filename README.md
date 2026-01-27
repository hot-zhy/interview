# AI 面试系统 (Java 技术面试)

一个基于 Streamlit 的 AI 面试系统，专注于 Java 技术面试，支持简历解析、题库管理、自适应出题和智能评分。

## 功能特性

- ✅ 用户认证（注册/登录/退出）
- ✅ 简历上传与解析（PDF/DOCX）
- ✅ Excel 题库导入与管理
- ✅ 自适应面试流程（基于难度和章节）
- ✅ 规则评分引擎（无需 LLM 即可运行）
- ✅ LLM 增强评分（可选）
- ✅ 数字人面试官（2D Avatar + TTS）
- ✅ 面试报告生成

## 安装步骤

### 1. 环境要求

- Python 3.11+
- pip

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，设置 SECRET_KEY 和数据库连接
```

在 `.env` 文件中配置 MySQL 数据库连接：

```env
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/interview_db?charset=utf8mb4
SECRET_KEY=your-secret-key-change-in-production
# 如需使用 LLM 增强评分，配置 ZHIPUAI_API_KEY（使用 GLM-4-Flash 模型）
ZHIPUAI_API_KEY=your-zhipuai-key
```

**注意**：请先创建 MySQL 数据库：

```sql
CREATE DATABASE interview_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. 初始化数据库

```bash
# 方式一：使用初始化脚本（推荐，会自动创建数据库）
python scripts/init_db.py

# 方式二：使用 Alembic
alembic upgrade head
```

详细数据库配置请参考 `DATABASE_SETUP.md`

### 5. 运行应用

```bash
streamlit run app/streamlit_app.py
```

应用将在 `http://localhost:8501` 启动。

## 使用指南

### 1. 注册/登录

- 首次使用需要注册账号
- 登录后进入主界面

### 2. 上传简历

- 在"简历管理"页面上传 PDF 或 DOCX 格式简历
- 系统自动解析为结构化信息
- 可手动编辑和修正解析结果

### 3. 导入题库

- 在"题库管理"页面上传 `question.xlsx`
- Excel 表头必须包含：`id`, `question`, `correct_answer`, `difficulty`, `chapter`
- 系统支持增量导入（按 id upsert）

### 4. 开始面试

- 在"面试"页面创建新面试
- 选择技术方向（track）、难度级别（level）
- 可选择是否基于简历定制题目
- 设置面试轮数（默认 10 轮）
- 在面试房间中回答问题，系统会自适应调整难度

### 5. 查看报告

- 面试结束后自动生成报告
- 包含分项评分、优势/短板、缺失知识点、学习建议和推荐题单

## 项目结构

```
repo/
  app/
    streamlit_app.py          # Streamlit 入口
    pages/                     # 多页面应用
      1_Auth.py               # 认证页面
      2_Resume.py             # 简历管理
      3_QuestionBank.py       # 题库管理
      4_Interview.py          # 面试房间
      5_Report.py             # 报告查看
      6_Admin.py              # 管理后台
    components/               # UI 组件
      avatar.py               # 数字人 Avatar
      tts.py                  # TTS 组件
      ui.py                   # 通用 UI
  backend/
    core/                     # 核心配置
      config.py
      security.py
      logging.py
    db/                       # 数据库
      base.py
      session.py
      models.py
      migrations/             # Alembic migrations
    schemas/                  # Pydantic schemas
    services/                 # 业务逻辑
  data/                       # 数据目录
    question.xlsx             # 示例题库（可选）
  tests/                      # 测试用例
  alembic.ini                 # Alembic 配置
  requirements.txt
  .env.example
  README.md
```

## 技术栈

- **UI**: Streamlit
- **数据库**: SQLite + SQLAlchemy 2.x
- **ORM**: SQLAlchemy + Alembic
- **安全**: passlib (bcrypt) + python-jose (JWT)
- **简历解析**: pdfplumber + python-docx
- **文本相似度**: rapidfuzz
- **配置管理**: pydantic-settings
- **测试**: pytest

## 运行测试

```bash
pytest tests/
```

## 注意事项

1. **无 LLM 模式**：系统可以在没有 LLM API Key 的情况下运行，使用规则评分引擎
2. **题库格式**：Excel 文件必须包含指定的表头，否则导入会失败
3. **浏览器兼容性**：数字人 TTS 功能依赖浏览器 Web Speech API，部分浏览器可能不支持
4. **数据安全**：生产环境请务必修改 `.env` 中的 `SECRET_KEY`

## 许可证

MIT License

