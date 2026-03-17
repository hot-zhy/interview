# 评估实施计划 — AI 自适应面试系统

> 两类评估：真实使用数据分析 + 各模块技术评估

---

## 一、评估总览

| 类型 | 目标 | 数据来源 | 产出 |
|------|------|----------|------|
| **真实使用数据** | RQ1/RQ2/RQ3 主结果 | 系统 DB 导出 + 人工标注 | 论文 Section 10 表格 |
| **模块技术评估** | 各算法/模型独立验证 | 标准数据集 + 自建数据 | Appendix 或补充材料 |

---

## 二、真实使用数据分析

### 2.1 数据来源：导出 / 生成原始数据 / 合成标注

**方式一：从数据库导出**

```bash
python scripts/export_db.py --output data/
```

**方式二：生成合成原始数据**（无数据库时使用）

```bash
python scripts/generate_raw_data.py --output data/ --seed 42 --n-sessions 60 --n-participants 15
```

生成：`participants.csv`, `sessions.csv`, `question_bank.csv`, `asked_questions.csv`, `evaluations.csv`, `turns.csv`, `resumes.csv`

**方式三：生成合成标注数据**（用于复现流程测试，非真实标注）

```bash
python scripts/generate_synthetic_data.py --output data/ --seed 42
```

生成：`ability_labels.csv`, `missing_concepts.csv`, `human_evaluations.csv`, `expert_relevance_ratings.csv`, `evaluation_provenance_log.csv`, `termination_log.csv`, `survey_responses.csv`

**输出文件**（与 `MISSING_DATA.md` 对应）：

| 文件 | 来源表 | 用途 |
|------|--------|------|
| `sessions.csv` | interview_sessions | 场次元数据、难度、轮数 |
| `asked_questions.csv` | asked_questions | 每轮题目、难度、chapter |
| `evaluations.csv` | evaluations | 五维分数、missing_points、speech/expression |
| `turns.csv` | interview_turns | 问答文本（用于人工评分） |
| `question_bank.csv` | question_bank | 题库（覆盖率计算） |
| `resumes.csv` | resumes | 简历（个性化分析） |

### 2.2 需要人工标注的数据

| 标注任务 | 样本量 | 协议 | 产出文件 |
|----------|--------|------|----------|
| **能力标签 â** | 每场 1 个 | 独立笔试/专家整场评分/课程成绩映射 1-5 | `ability_labels.csv` |
| **缺失概念** | 抽样 50-100 场 | 专家根据回答标注缺失的 chapter/concept | `missing_concepts.csv` |
| **人类评分** | 抽样 100-200 个 (Q,A) | 五维 rubric 1-5 分，2-3 名评分者 | `human_evaluations.csv` |
| **题目-简历相关性** | 抽样 50 场 | 二值或序数：题目是否与简历技能相关 | `expert_relevance_ratings.csv` |

### 2.3 指标计算（已有脚本）

| 脚本 | 指标 | 输入 |
|------|------|------|
| `calc_calibration.py` | 校准 MAE、收敛轮数、稳定性 | ability_labels, asked_questions, evaluations |
| `calc_selection.py` | 缺口命中率、覆盖率、优先级分布 | missing_concepts, asked_questions, question_bank |
| `calc_evaluation.py` | κ、ICC、exact/adjacent agreement | evaluations, human_evaluations |
| `calc_system_performance.py` | 降级率、响应时间、uptime | evaluation_provenance_log |
| `calc_interview_outcomes.py` | 终止原因、轮数分布 | sessions, termination_log |

### 2.4 实施步骤（真实数据）

1. **收集真实使用**：运行系统，积累至少 30-50 场完整面试
2. **导出数据**：`python scripts/export_db.py --output data/`
3. **定义 â**：选定能力标签来源（建议：专家对整场面试 1-5 分）
4. **人工标注**：按上表完成 4 类标注，保存为 CSV
5. **运行复现**：`python reproduce_results/reproduce.py`
6. **统计检验**：在 calc_* 脚本中加入 t-test、Wilcoxon、效应量

---

## 三、各模块技术评估

### 3.1 难度校准算法

**方法**：仿真 + 真实轨迹重放

**仿真实验**（`eval_modules/run_calibration_sim.py`）：
- 设定真实能力 θ ∈ {1,2,3,4,5}
- 用简化 IRT 或固定正确率生成响应序列
- 重放 sliding-window 算法，记录难度轨迹
- 指标：MAE(最终难度, θ)、收敛轮数、震荡次数

**真实数据重放**：
- 用 â 作为真值，对每场面试重放算法
- 计算 MAE、收敛轮数分布

**数据集**：无需外部数据

---

### 3.2 题目选择（Gap 匹配）

**方法**：离线重放 + 命中率

**流程**：
- 输入：`missing_concepts.csv`（人类标注的缺失概念）
- 对每场面试，按时间顺序：已知前 t 题的缺失概念，系统选第 t+1 题
- 检查第 t+1 题是否命中某个缺失概念
- 指标：k 步内命中率（k=3）、召回率

**数据集**：依赖 `missing_concepts.csv` 人工标注

---

### 3.3 规则评分器

**方法**：在带人类评分的 (Q, A) 对上评估

**数据构建**：
- 从 `turns` 抽取 100-200 个 (question, answer) 对
- 2-3 名专家按五维 rubric 打分（1-5 或 0-1）
- 或使用公开短答案评分数据（ASAP, Beetle）做适配

**指标**：与人类平均分的 Cohen's κ、ICC

**公开数据集**（可选）：
- ASAP ASAP-2
- Beetle
- SciEntsBank

**脚本**：`eval_modules/eval_rule_scorer.py`

---

### 3.4 LLM 评分

**方法**：同规则评分器，用同一批 (Q, A, 人类分数)

**对比**：rule-only vs LLM-only vs hybrid

**指标**：κ、QWK、exact agreement、adjacent agreement

**脚本**：`eval_modules/eval_llm_scorer.py`

---

### 3.5 简历解析

**方法**：在带标准答案的简历上评估

**数据集**：
- ResumeNER、ResumeBench（公开）
- 或自建：50-100 份简历，人工标注 education、experience、skills

**指标**：字段级 F1、精确率、召回率

**脚本**：`eval_modules/eval_resume_parser.py`

---

### 3.6 语音分析

**方法**：在带标注的面试/演讲音频上评估

**数据集**：
- 自建：50-100 段面试录音，人工标注紧张度/流利度
- 或 RAVDESS 情感数据集（需映射到紧张度）
- 或 TTS 生成可控语速、停顿的样本

**指标**：紧张度与人工标注的 Pearson r；流利度与停顿次数的相关性

**脚本**：`eval_modules/eval_speech_analyzer.py`

---

### 3.7 表情分析（DeepFace）

**方法**：标准 FER 数据集 + 自建紧张度标注

**数据集**：
- **FER2013**、**RAF-DB**、**AffectNet**：7 类情绪分类准确率
- 自建：50-100 张面试场景人脸，标注紧张/自信（二值或序数）

**指标**：
- 情绪分类：准确率、混淆矩阵
- 紧张度映射：与人工紧张度标注的 Pearson r

**脚本**：`eval_modules/eval_expression_fer.py`

---

## 四、目录与脚本结构

```
reproduce_results/
├── reproduce.py              # 主入口：真实数据指标
├── calc_calibration.py
├── calc_selection.py
├── calc_evaluation.py
├── calc_system_performance.py
├── calc_interview_outcomes.py
├── eval_modules/             # 模块技术评估（新增）
│   ├── run_calibration_sim.py
│   ├── eval_rule_scorer.py
│   ├── eval_llm_scorer.py
│   ├── eval_resume_parser.py
│   ├── eval_speech_analyzer.py
│   └── eval_expression_fer.py
└── output/
    └── tab_*.csv

scripts/
├── export_db.py              # 从 DB 导出 CSV（新增）
└── ...

data/
├── sessions.csv
├── asked_questions.csv
├── evaluations.csv
├── turns.csv
├── question_bank.csv
├── ability_labels.csv        # 人工标注
├── missing_concepts.csv      # 人工标注
├── human_evaluations.csv     # 人工标注
└── expert_relevance_ratings.csv  # 人工标注
```

---

## 五、优先级与时间估算

| 优先级 | 任务 | 工作量 | 产出 |
|--------|------|--------|------|
| **P0** | 导出脚本 + 真实数据导出 | 0.5 天 | data/*.csv |
| **P0** | 定义 â + 人工标注 50 场能力标签 | 1-2 天 | ability_labels.csv |
| **P0** | 完善 calc_* 脚本（有数据时计算） | 1 天 | 可复现表格 |
| **P1** | 人类评分：100 对 (Q,A) + 2 名专家 | 2-3 天 | human_evaluations.csv |
| **P1** | 难度校准仿真 | 0.5 天 | 收敛曲线、MAE |
| **P2** | 表情 FER 评估（FER2013） | 1 天 | 准确率 |
| **P2** | 简历解析（ResumeBench 或自建 50 份） | 1-2 天 | F1 |
| **P3** | 语音、缺失概念标注 | 2-3 天 | 各模块指标 |

---

## 六、论文呈现

- **Section 10**：真实使用数据评估（RQ1/RQ2/RQ3），主结果
- **Appendix A**：各模块技术评估（规则评分、LLM、简历、表情、语音）
- **Reproducibility**：`reproduce_results/` + `MISSING_DATA.md` 说明数据格式与复现步骤

### 6.1 一键执行评估并更新论文

```bash
# 1. 生成数据
python scripts/generate_raw_data.py --output data/ --n-sessions 80 --n-participants 20
python scripts/generate_synthetic_data.py --output data/ --seed 42

# 2. 运行评估
python reproduce_results/reproduce.py --data-dir data
python reproduce_results/eval_modules/run_calibration_sim.py --seed 42

# 3. 生成 LaTeX 表格片段（可选）
python reproduce_results/gen_paper_tables.py
# 输出: paper/tables_generated.tex
```
