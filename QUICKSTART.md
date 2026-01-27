# 快速开始指南

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

## 2. 配置环境变量

复制 `.env.example` 为 `.env`（如果还没有创建）：

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

编辑 `.env` 文件，配置数据库连接和密钥：

```
# MySQL 数据库配置（必填）
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/interview_db?charset=utf8mb4

# 安全密钥（必填）
SECRET_KEY=your-secret-key-here-change-in-production

# LLM 配置（可选）
ZHIPUAI_API_KEY=your-zhipuai-key
ZHIPUAI_MODEL=glm-4-flash
```

**重要**：在初始化数据库前，请先创建 MySQL 数据库：

```sql
CREATE DATABASE interview_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

或者使用命令行：

```bash
mysql -u root -p -e "CREATE DATABASE interview_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

## 3. 安装 MySQL 驱动

```bash
pip install pymysql cryptography
```

或重新安装所有依赖：

```bash
pip install -r requirements.txt
```

## 4. 初始化数据库

**方式一：使用初始化脚本（推荐）**

```bash
python scripts/init_db.py
```

此脚本会自动创建数据库（如果不存在）和所有表。

**方式二：使用 Alembic**

```bash
alembic upgrade head
```

## 5. 运行应用

```bash
streamlit run app/streamlit_app.py
```

或者使用快速启动脚本：

```bash
python run.py
```

应用将在 `http://localhost:8501` 启动。

## 6. 导入题库

1. 登录系统（首次使用需要注册）
2. 进入"题库管理"页面
3. 上传 `question.xlsx` 文件（格式见 `data/README.md`）
4. 点击"导入题库"

## 7. 开始使用

1. **上传简历**（可选）：在"简历管理"页面上传 PDF 或 DOCX 格式简历
2. **创建面试**：在"面试"页面选择技术方向、难度等，开始面试
3. **回答问题**：在面试房间中回答面试官的问题
4. **查看报告**：面试结束后在"报告"页面查看详细评价

## 注意事项

- 系统可以在没有 LLM API Key 的情况下运行，使用规则评分引擎
- 首次使用前必须导入题库，否则无法开始面试
- 数字人 TTS 功能依赖浏览器 Web Speech API，部分浏览器可能不支持

## 运行测试

```bash
pytest tests/
```

## 故障排除

### 数据库连接错误

如果遇到数据库连接错误：

1. **检查 MySQL 服务是否运行**
   ```bash
   # Windows
   net start mysql
   
   # Linux/Mac
   sudo systemctl start mysql
   ```

2. **检查数据库是否存在**
   ```sql
   SHOW DATABASES;
   ```
   如果 `interview_db` 不存在，创建它：
   ```sql
   CREATE DATABASE interview_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. **检查连接配置**
   确保 `.env` 文件中的 `DATABASE_URL` 配置正确：
   ```
   DATABASE_URL=mysql+pymysql://用户名:密码@主机:端口/数据库名?charset=utf8mb4
   ```

4. **重新初始化数据库**
   ```bash
   python scripts/init_db.py
   ```

### 表不存在错误

如果遇到 "no such table" 错误，说明数据库表未创建：

```bash
# 运行初始化脚本
python scripts/init_db.py

# 或使用 Alembic
alembic upgrade head
```

### 导入题库失败

确保 Excel 文件包含正确的表头：`id`, `question`, `correct_answer`, `difficulty`, `chapter`

### TTS 不工作

这是正常的，TTS 功能依赖浏览器支持。如果浏览器不支持 Web Speech API，系统会自动降级为仅文字显示。

