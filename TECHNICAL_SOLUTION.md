## AI 面试系统技术方案总览

本系统是一个面向 **Java 技术面试** 的 AI 面试平台，基于 **Streamlit** 提供 Web UI，后端使用 **Python + SQLAlchemy** 管理数据与业务逻辑，结合 **自适应出题算法** 和 **规则/LLM 混合评分机制**，实现从简历解析、题库管理到面试流程与报告生成的一体化闭环。

- **主要能力**：用户认证、简历上传与解析、Excel 题库导入、自适应问答流程、规则评分与可选 LLM 增强、数字人面试官（Avatar + TTS）、多维度面试报告。
- **运行模式**：支持 **无 LLM 完全规则引擎模式**，也支持接入 **Zhipu AI（GLM-4-Flash）** 做评分增强与自然语言处理。

---

## 系统架构

### 整体架构分层

- **前端/UI 层（`app/`）**
  - 基于 **Streamlit** 的多页面应用：
    - `1_Auth.py`：认证页面（注册/登录/退出）
    - `2_Resume.py`：简历管理与解析
    - `3_QuestionBank.py`：题库导入与维护
    - `4_Interview.py`：面试房间，自适应问答流程
    - `5_Report.py`：面试结果与报告展示
    - `6_Admin.py`：管理后台
  - `components/`：可复用 UI 组件
    - `avatar.py`：2D 数字人面试官渲染
    - `tts.py`：基于浏览器 Web Speech API 的文本转语音封装
    - `ui.py`：通用布局与交互组件

- **后端服务层（`backend/`）**
  - `core/`
    - `config.py`：系统配置、环境变量读取（基于 `pydantic-settings`）
    - `security.py`：密码加密（`passlib[bcrypt]`）、JWT 令牌管理（`python-jose`）
    - `logging.py`：日志配置
  - `db/`
    - `base.py`：SQLAlchemy Base 定义
    - `session.py`：数据库 Session 工厂
    - `models.py`：核心数据模型（用户、简历、题目、面试会话、答题记录、评分等）
    - `migrations/`：Alembic 迁移脚本
  - `schemas/`：Pydantic Schema，定义 API/内部服务的数据输入输出结构
  - `services/`：
    - `adaptive_interview.py`：自适应面试核心算法
    - `interview_engine.py`：面试状态机和业务流程编排
    - `question_selector.py`：智能题目选择逻辑
    - 其他如简历解析、题库导入、规则评分引擎、LLM 调用等服务模块

- **数据与存储层（`data/` + DB）**
  - 默认支持 **MySQL**（推荐生产）与 **SQLite**（快速本地开发）。
  - `data/` 下存放示例题库 `question.xlsx` 及本地 SQLite 文件（可选）。
  - 通过 `.env` 中 `DATABASE_URL` 统一配置数据库连接。

---

## 技术栈与依赖

- **UI**：Streamlit
- **数据库**：MySQL / SQLite + SQLAlchemy 2.x
- **ORM & 迁移**：SQLAlchemy + Alembic
- **认证与安全**：passlib (bcrypt)、python-jose (JWT)
- **简历解析**：pdfplumber（PDF）、python-docx（DOCX）
- **文本相似度**：rapidfuzz（模糊匹配、相似度计算）
- **配置管理**：pydantic-settings
- **测试**：pytest
- **可选 LLM**：ZhipuAI GLM-4-Flash（通过 `ZHIPUAI_API_KEY`、`ZHIPUAI_MODEL` 配置）

---

## 部署与运行方案

### 环境与依赖

- **运行环境**：Python 3.11+
- **安装依赖**：

```bash
pip install -r requirements.txt
```

### 数据库配置

- 推荐使用 MySQL 8.0+，创建数据库：

```sql
CREATE DATABASE interview_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

- `.env` 中配置示例：

```env
# MySQL
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/interview_db?charset=utf8mb4

# 也可切换为 SQLite
# DATABASE_URL=sqlite:///./data/interview.db

SECRET_KEY=your-secret-key-change-in-production

# 可选 LLM
ZHIPUAI_API_KEY=your-zhipuai-key
ZHIPUAI_MODEL=glm-4-flash
```

- 安装 MySQL 驱动：

```bash
pip install pymysql cryptography
```

### 数据库初始化

- **方式一（推荐）**：初始化脚本

```bash
python scripts/init_db.py
```

- **方式二**：Alembic 迁移

```bash
alembic upgrade head
```

### 启动应用

```bash
# 方式一
streamlit run app/streamlit_app.py

# 方式二（如果提供 run.py 快速启动）
python run.py
```

应用默认运行在 `http://localhost:8501`。

---

## 核心业务流程

### 1. 用户认证

- 用户注册、登录、退出，密码使用 bcrypt 单向加密。
- 登录后后端使用 JWT 管理会话，配合 Streamlit Session State 进行前端状态维护。

### 2. 简历管理与解析

- 在“简历管理”页面上传 PDF/DOCX 简历。
- 后端调用 `pdfplumber` / `python-docx` 对简历内容进行解析，抽取：
  - 个人信息
  - 教育背景
  - 工作经历
  - 项目经验
  - 技能关键字
- 解析结果以结构化数据写入数据库，并在前端提供编辑能力，用于：
  - 后续题目选择时进行技能匹配
  - 调整章节权重，突出候选人声称擅长的方向。

### 3. 题库管理

- 在“题库管理”页面导入 `question.xlsx`：
  - 必须包含表头：`id`, `question`, `correct_answer`, `difficulty`, `chapter`
  - 通过 `id` 做 upsert，支持增量导入与更新。
- 后端将题目写入 `Question` 模型，包括：
  - 题干文本
  - 标准答案
  - 难度等级
  - 所属章节/知识点

### 4. 自适应面试流程

- 在“面试”页面创建面试 Session：
  - 选择技术方向（track）、目标难度（level）
  - 是否基于简历定制题目
  - 设置计划轮次（默认 10 轮）
- 面试进行中：
  - 每轮根据自适应算法从题库中选择下一道题。
  - 候选人回答后，规则评分引擎（可选叠加 LLM 评分）输出本题得分、缺失点等。
  - 自适应算法根据最近表现调整下一轮难度、决定是否追问、判断是否结束面试。
  - 前端通过数字人 Avatar 和 TTS 展示题目与反馈（浏览器支持时）。

### 5. 评分与报告生成

- **规则评分引擎（必选）**：
  - 不依赖外部 LLM，通过若干规则进行评分，例如：
    - 关键词覆盖度
    - 结构与条理性
    - 重要点是否提及
  - 输出标准化得分（0–1），并标记缺失知识点。

- **LLM 增强评分（可选）**：
  - 如果在 `.env` 中配置了 `ZHIPUAI_API_KEY`，可调用 ZhipuAI GLM-4-Flash：
    - 对开放式回答进行语义理解
    - 提供更细粒度的评价与建议
    - 与规则引擎得分做加权或对齐

- **面试报告**：
  - 总体评分与等级
  - 维度化评分：如基础、并发、JVM、框架、工程实践等
  - 优势与短板总结
  - 缺失/薄弱知识点列表
  - 后续学习建议与推荐练习题单（按章节与难度组合）。

---

## 自适应算法设计

> 主要代码文件：`backend/services/adaptive_interview.py`、`interview_engine.py`、`question_selector.py`。

### 1. 自适应难度调整算法

- **名称**：基于滑动窗口的加权难度调整算法  
- **目标**：根据候选人最近的表现自动提高或降低题目难度，避免固定难度带来的“偏难或偏易”问题。

#### 1.1 核心思想

- 维护一个大小为 \(N\)（默认 `window_size=3`）的滑动窗口，记录最近几题得分 \(\{score_1, ..., score_N\}\)。
- 使用越近权重越大的加权平均：最近一题权重最大。
- 结合最近两题分数差的趋势（上升/下降）决定是否调整难度。

#### 1.2 关键计算公式

- 加权平均分（权重为序号 1, 2, ..., n）：

\[
weighted\_avg = \frac{\sum_{i=1}^{n} score_i \cdot i}{\sum_{i=1}^{n} i}
\]

- 趋势：

\[
trend = score_n - score_{n-1}
\]

- 新难度为：

\[
new\_difficulty = f(weighted\_avg, trend, current\_difficulty)
\]

其中 \(f\) 按阈值与趋势进行离散调整。

#### 1.3 决策规则（示意）

- \(weighted\_avg \ge 0.8\) 且 \(trend > 0.1\) → **提高难度**
- \(weighted\_avg \ge 0.75\) → **保持难度**
- \(0.6 \le weighted\_avg < 0.75\)：
  - \(trend > 0.05\) → 略微提高难度
  - \(trend < -0.05\) → 略微降低难度
- \(weighted\_avg < 0.6\) → **降低难度**

---

### 2. 智能追问判断算法

- **名称**：基于表现和缺失点的追问决策算法  
- **目标**：只在有价值的情况下追问，避免“无限追问”或重复提问。

#### 2.1 核心思想

- 对单个问题限制 **最多 2 次追问**（`followup_limit=2`）。
- 结合本题得分与识别出的缺失点（`missing_points`）判断是否需要追问。
- 通过文本相似度判断，避免问与之前高度相似的问题。

#### 2.2 决策规则

1. **追问次数限制**
   - 若 `followup_count >= 2` → 不再追问。

2. **相似题检测**
   - 如果题库或历史记录中已存在相似度 > 阈值（默认 70%）的问题 → 不追问同类问题。

3. **追问条件示例**
   - 条件 1：`score < 0.6` 且 `missing_points > 0` → **追问**，重点查缺补漏。
   - 条件 2：`0.6 ≤ score < 0.7` 且 `missing_points > 0` 且 `followup_count < 1` → **允许一次补充追问**。

#### 2.3 文本相似度计算

- 使用 RapidFuzz 的 `partial_ratio` 函数：

\[
similarity = \text{partial\_ratio}(\text{text1.lower()}, \text{text2.lower()})
\]

- 当 `similarity > 70` 时视为相似问题，一般不再追问或重复提问。

---

### 3. 智能结束判断算法

- **名称**：多维度综合评估的结束决策算法  
- **目标**：在保证覆盖度与稳定性的前提下，智能判断是否提前结束或延长面试。

#### 3.1 指标定义

- **平均分**：

\[
avg\_score = \frac{\sum_{i=1}^{n} score_i}{n}
\]

- **最近表现平均分**：

\[
recent\_avg = \frac{\sum score_i}{k}, \quad k = \min(window\_size, n)
\]

- **稳定性（标准差）**：

\[
variance = \frac{\sum (score_i - avg\_score)^2}{n}, \quad std\_dev = \sqrt{variance}
\]

- **难度覆盖度**：

\[
difficulty\_range = \max(difficulties) - \min(difficulties)
\]

- **章节覆盖度**：

\[
chapter\_coverage = |\text{unique\_chapters}|
\]

- 轮次约束：
  - `min_rounds = 5`
  - `max_rounds = 15`

#### 3.2 结束条件示意

- **提前结束（表现优秀）**：
  - \(avg\_score \ge 0.85\)、\(recent\_avg \ge 0.85\)、\(std\_dev < 0.15\)、轮次 ≥ `min_rounds + 2`

- **提前结束（表现较差且无改善）**：
  - \(avg\_score < 0.4\)、\(recent\_avg < 0.4\)、轮次 ≥ `min_rounds`

- **正常结束**：
  - \(std\_dev < 0.2\)
  - `difficulty_range ≥ 2`
  - `chapter_coverage ≥ 3`
  - `recent_avg ≥ 0.7`

- **强制结束**：
  - 轮次 ≥ `max_rounds`

---

### 4. 智能题目选择算法

- **名称**：基于章节权重和知识缺口的题目选择算法  
- **目标**：在保证章节与难度覆盖的前提下，优先抽查候选人薄弱或简历相关的知识点，同时避免重复提问。

#### 4.1 核心思想

- 维护面试过程中的以下集合：
  - **已覆盖章节**：避免短时间内重复考察。
  - **薄弱章节/缺失章节（`missing_chapters`）**：根据历史得分动态计算。
  - **简历技能对应章节**：从简历解析中抽取技能，映射到章节标签。

- 选择优先级：
  1. **缺失/薄弱章节**：优先从 `missing_chapters` 中选题，快速定位候选人短板。
  2. **简历技能匹配章节**：对简历中声明的强项进行适度“加压”，但避免最近 2 轮重复。
  3. **按 track 配置章节权重的加权随机**：确保面试方向内核心章节基本覆盖，并保持一定随机性。

#### 4.2 章节模糊匹配

- 章节命名可能存在多种写法（如 “Java 并发” vs “并发编程”），使用 RapidFuzz 的 `partial_ratio` 进行模糊匹配。

- 伪代码示例：

```python
from rapidfuzz import fuzz

def fuzzy_match_chapter(track_chapters, target):
    for chapter in track_chapters:
        similarity = fuzz.partial_ratio(chapter.lower(), target.lower())
        if similarity > 70:  # 70% 相似度阈值
            return chapter
    return None
```

---

## 算法参数与可调优项

### 1. 可调参数

- **followup_limit（默认 2）**：每个问题最多追问次数。
- **min_rounds（默认 5）**：最少面试轮次。
- **max_rounds（默认 15）**：最多面试轮次。
- **window_size（默认 3）**：滑动窗口大小。
- **similarity_threshold（默认 70%）**：文本相似度阈值。
- **excellent_score（默认 0.85）**：优秀分数阈值。
- **poor_score（默认 0.4）**：较差分数阈值。
- **stability_threshold（默认 0.15）**：稳定性阈值（标准差）。

### 2. 难度调整区间

- `weighted_avg ≥ 0.8` 且 `trend > 0.1` → 提高难度。
- `weighted_avg ≥ 0.75` → 保持难度。
- `0.6 ≤ weighted_avg < 0.75` 且 `trend > 0.05` → 提高难度。
- `0.6 ≤ weighted_avg < 0.75` 且 `trend < -0.05` → 降低难度。
- `weighted_avg < 0.6` → 降低难度。

---

## 方案优势与后续优化方向

- **自适应性强**：根据实时表现动态调整难度、追问次数和面试时长，而非固定脚本。
- **多维度评估**：综合分数、稳定性、难度与章节覆盖进行决策，更接近真实面试官行为。
- **可解释性好**：每一步决策均有明确的公式、阈值和规则，便于对外说明与内部调试。
- **部署灵活**：既可以在 **无 LLM 环境** 下稳定运行，也可以轻量接入 **ZhipuAI** 提升语义理解与评分效果。
- **可演进性**：后续可以在自适应算法中引入更复杂模型（如 IRT、Multi-Armed Bandit、强化学习），当前规则式设计为后续演进提供基础数据和评估框架。


