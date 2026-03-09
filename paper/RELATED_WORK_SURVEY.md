# 相关论文调研报告 — AI 自适应面试系统

> 用于汇报：论文定位、评估方法参考、数据分析对标

---

## 一、研究定位

我们的系统是一个**自适应 AI 技术面试系统**，核心解决三个问题：
- **RQ1**: 实时难度校准（lightweight sliding-window，不依赖预校准 IRT）
- **RQ2**: 多优先级题目选择（知识缺口 + 简历个性化 + LLM 方向反馈 + 覆盖率）
- **RQ3**: 混合评估框架（规则 + LLM 增强 + 自动降级），含表情与语音辅助分析

以下论文按与我们系统的关联度排序。

---

## 二、核心相关论文（Top 5 精读推荐）

### 2.1 Conversate — LLM 驱动的面试模拟与反思学习
- **标题**: Conversate: Supporting Reflective Learning in Interview Practice Through Interactive Simulation and Dialogic Feedback
- **来源**: arXiv:2410.05570 (CHI 相关, 2024-2025)
- **系统**: LLM 驱动的交互式面试模拟，支持自适应追问 + 对话式反馈
- **评估方法**:
  - 19 人用户研究（within-subjects）
  - 半结构化访谈 → 主题分析（thematic analysis）
  - Likert 量表描述性统计
- **核心发现**: 自适应追问提升真实感；AI 辅助标注降低认知负荷；双向对话反馈优于单向反馈
- **与我们的关系**: 最接近我们系统的工作。我们额外提供了难度校准、多维评分、表情分析、规则降级

### 2.2 AI Mock Interview Scoring — LLM 评分一致性
- **标题**: AI-driven mock interview assessment: leveraging generative language models for automated evaluation
- **来源**: International Journal of Machine Learning and Cybernetics (Springer, 2025)
- **系统**: GPT-3.5 对面试回答自动评分
- **评估方法**:
  - LLM 评分 vs 人类评分
  - Cohen's κ，Pearson 相关系数
  - 混淆矩阵分析
  - HR 题与技术题分开评估
- **核心发现**: LLM 在技术题评分上接近人类一致性
- **与我们的关系**: 直接对标 RQ3，我们的 hybrid 方案进一步保证了降级可用性

### 2.3 ROAR-CAT — 自适应测试开发与验证黄金流程
- **标题**: ROAR-CAT: Rapid Online Assessment of Reading ability with Computerized Adaptive Testing
- **来源**: Behavior Research Methods (Springer, 2025)
- **系统**: JavaScript 实现的 CAT 阅读能力评估
- **评估方法**:
  - 开发阶段: 1960 名学生建立 IRT 参数
  - 验证阶段: 485 名学生 CAT vs 固定测试对比
  - Pearson 相关 (r=.89)
  - 效率对比: 75 题 CAT ≈ 125 题固定测试
  - Test-retest 信度
- **核心发现**: CAT 可在保持测量精度的前提下减少 40% 题目
- **与我们的关系**: 对标 RQ1，但我们场景不需要预校准 IRT，用 sliding-window 替代

### 2.4 LLM Formative Assessment Scoring — 自动评分可靠性
- **标题**: Evaluating LLMs for Automated Scoring in Formative Assessments
- **来源**: MDPI Applied Sciences, 2025 (doi:10.3390/app15052787)
- **评估方法**:
  - Quadratic Weighted Kappa (QWK)
  - Exact agreement rate + adjacent agreement rate
  - 多 prompt 策略对比（zero-shot, few-shot, CoT）
- **核心发现**: 精心设计的 prompt 可显著提升 LLM-人类评分一致性
- **与我们的关系**: 直接对标我们的 hybrid evaluation agreement 分析方法

### 2.5 Adaptive Learning 大规模对照实验
- **标题**: Using an adaptive learning tool to improve student performance and satisfaction
- **来源**: Smart Learning Environments (Springer, 2024)
- **评估方法**:
  - 500 名本科生，between-subjects（AL 实验组 vs 传统 LMS 对照组）
  - 两学期纵向追踪
  - 独立样本 t-test，效应量 Cohen's d
  - 学习日志分析
  - 问卷（满意度 + 参与度）
- **核心发现**: AL 在线上/线下均显著提升成绩 (p < 0.05)
- **与我们的关系**: between-subjects 实验设计模板

---

## 三、补充相关论文

### 3.1 模块化 AI 面试官 (arXiv:2601.11534, 2025)
- 本地 LLM，动态出题 + 实时能力画像
- 满意度 4.45/5，参与度 4.33/5
- SUS 可用性量表
- **参考**: 模块化架构设计思路

### 3.2 AI-Powered Adaptive Learning UX (Frontiers in CS, 2025)
- 23 人，3 平台对比
- SUS + NASA-TLX 认知负荷 + 任务完成时间
- **参考**: 用户体验评估指标组合

### 3.3 LLM Scoring Rationale Comparison (arXiv:2509.23412, 2025)
- 不仅比较评分分数，还比较评分理由
- Cohen's κ + 理由编码分析
- **参考**: hybrid evaluation 的理论支撑

### 3.4 65 篇 LLM-AES Meta-Analysis (arXiv:2512.14561, 2025)
- κ 和相关系数范围 0.30-0.80
- 覆盖不同任务类型、模型、prompt 策略
- **参考**: 用于定位我们 agreement 数值在文献中的位置

### 3.5 EvalNet 多模态面试评估 (2025)
- 音频 + 视频 + 文本融合
- 情感检测 F1-score 对比（单模态 vs 多模态）
- **参考**: 表情分析模块的文献支撑

### 3.6 HireVue 表情分析反思
- 面部表情仅解释 0.25% 的工作表现方差
- HireVue 已降低表情评分权重
- **参考**: 支撑我们将表情作为 auxiliary feature 的设计决策

### 3.7 CAT Validity Testing Framework (2024)
- IRT 题库验证 + 模拟 CAT + 真实 CAT + 公平性分析
- DIF 分析，多组比较
- **参考**: validity testing 系统框架

---

## 四、评估方法论总结（各论文共性）

### 4.1 用户研究规模
| 场景 | 典型人数 | 设计 |
|------|---------|------|
| HCI / CHI | 15-30 | within-subjects, think-aloud |
| 教育研究 | 100-500 | between-subjects, 纵向 |
| 系统验证 | 20-50 | mixed methods |

### 4.2 常用量表与指标
| 指标 | 用途 | 来源论文 |
|------|------|---------|
| SUS (System Usability Scale) | 系统可用性 | 3.1, 3.2 |
| NASA-TLX | 认知负荷 | 3.2 |
| Likert 5/7-point | 满意度、信心 | 2.1, 3.1 |
| Cohen's κ / QWK | 评分一致性 | 2.2, 2.4, 3.3 |
| ICC (Intraclass Correlation) | 连续分数信度 | 2.4 |
| Pearson r | 效标关联效度 | 2.3 |

### 4.3 常用统计检验
| 检验方法 | 适用场景 | 来源论文 |
|---------|---------|---------|
| Paired t-test / Wilcoxon | 前后测对比 | 2.1 |
| Independent t-test | 组间对比 | 2.5 |
| Cohen's d | 效应量 | 2.5 |
| ANOVA + Bonferroni | 多组比较 | 我们论文 |
| Bootstrap CI | 置信区间 | 我们论文, 2.4 |
| Kaplan-Meier / Cox | 面试长度分析 | 我们论文 |

### 4.4 质性分析方法
- **主题分析 (Thematic Analysis)**: 对访谈数据编码 → 提取主题 (2.1)
- **开放式问卷编码**: 归纳式编码 (2.1)
- **评分理由比较**: LLM vs 人类的推理过程对比 (3.3)

---

## 五、我们论文的定位（Positioning Statement）

> 相较于已有工作，我们的系统在以下方面具有独特贡献：

| 维度 | 现有最佳 | 我们的方案 | 优势 |
|------|---------|-----------|------|
| 难度校准 | ROAR-CAT (IRT) | Sliding-window (无需预校准) | 4-5 题收敛，无冷启动 |
| 题目选择 | 单优先级 | 多优先级 + LLM 方向反馈 | 统一框架平衡多目标 |
| 评分 | LLM-only 或 rule-only | Hybrid + 自动降级 | 兼顾准确性与可用性 |
| 报告 | 分数+简单反馈 | LLM 增强报告 + 规则降级 | 个性化学习建议 |
| 多模态 | 音频 或 表情（二选一） | 音频 + 实时表情 | 辅助信号不做决策 |
| 可用性 | 依赖外部 API | 全链路降级 | 99%+ 可用性 |

---

## 六、引用格式（BibTeX Keys）

以下是需要添加到 `references.bib` 的新引用，论文中使用 `\cite{key}` 引用：

```
conversate2024, evalnet2025, roarcat2025, llm_formative2025, 
adaptive_learning_sle2024, modular_interviewer2025, 
llm_scoring_meta2025, hirevue_expression2024
```
