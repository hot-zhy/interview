# 论文叙述到代码模块映射（当前实现）

> 目的：把 `paper/main.tex` 中的方法叙述与代码位置一一对应，方便查证“论文写了什么、代码落在哪里”。

## 1. 总入口与核心流程

### 论文位置
- 方法总框架：`sec:method`
- 闭环公式：`eq:agentic_loop`

### 代码位置
- 面试流程入口：`backend/services/interview_engine.py`
  - `start_interview(...)`
  - `submit_answer(...)`
  - `_submit_answer_agentic(...)`（feature flag 打开时）

说明：`submit_answer` 串起“写入回答 -> 评估 -> 状态更新 -> 追问/下一题/终止”。

## 2. Observation / Memory / State

### 论文位置
- Observation：`sec:observation`
- Interview Memory：`sec:memory`
- State Representation：`sec:state`

### 代码位置
- 数据模型（会话、轮次、评分、报告）：`backend/db/models.py`
- Agent 侧结构化模型：`backend/agent/models.py`
- Memory 聚合：`backend/agent/memory.py`
- State 构建：`backend/agent/state_builder.py`

说明：论文里的 `o_t, m_t, s_t` 在实现中分别对应“当前答题观测、数据库+agent memory 聚合、状态压缩对象”。

## 3. Planner / Controller（动作空间）

### 论文位置
- Controller：`sec:controller`
- 动作空间：`ask-next / follow-up / terminate`

### 代码位置
- 控制器：`backend/agent/controller.py`（`class AgentController`）
- 动作分发：controller + `backend/agent/tools.py`

说明：控制逻辑是结构化规则，不是自由生成；与论文“可审计、受限动作”一致。

## 4. RQ1：Adaptive Control（难度与终止）

### 论文位置
- `sec:adaptive_control`
- 算法：`alg:rq1`

### 代码位置
- `backend/services/adaptive_interview.py`
  - 难度更新
  - 终止判断
  - 追问预算与相关统计

说明：论文的滑窗、边界回合、终止条件，在该模块内实现为可配置策略。

## 5. RQ2：State-Aware Selection（选题）

### 论文位置
- `sec:selection`
- 目标函数：`eq:selection_objective`
- 算法：`alg:rq2`

### 代码位置
- `backend/services/question_selector.py`
  - `select_question(...)`
  - 多 priority 级联
  - LLM topic planner 融合入口
- `backend/services/personalized_algorithms.py`
  - ability / UCB / personalized 权重相关计算
- LLM 侧 topic 建议：`backend/services/llm_provider.py`（`suggest_next_topic_llm`）

说明：实现采用“priority cascade + 可选 LLM planner”，与论文描述一致。

## 6. Follow-up Planning（追问）

### 论文位置
- `sec:followup`
- 算法：`alg:followup`

### 代码位置
- 传统路径：`backend/services/interview_engine.py`（`_generate_followup`）
- Agent 路径：`backend/agent/followup_planner.py`
- 话术模板：`backend/services/interview_phrases.py`
- LLM 追问生成：`backend/services/llm_provider.py`（`generate_followup_with_context`）

说明：包含触发阈值、重复检测、每题追问上限与 LLM/模板回退。

## 7. RQ3：Hybrid Judging（评估）

### 论文位置
- `sec:hybrid_judging`
- 算法：`alg:rq3`

### 代码位置
- 规则评估：`backend/services/evaluator_rules.py`
- LLM 评估：`backend/services/llm_provider.py`（`evaluate_with_llm`）
- 路由与验证：`backend/agent/judge_router.py`
- 引擎内回退逻辑：`backend/services/interview_engine.py`（`_evaluate_answer_with_fallback`）

说明：论文中的 routing / validation / fallback / optional multi-judge 在代码中均有对应入口。

## 8. Tool-Augmented Architecture（工具化）

### 论文位置
- `sec:tools`
- 表格：`tab:tools`

### 代码位置（按工具）
- Rule scorer：`backend/services/evaluator_rules.py`
- LLM judge：`backend/services/llm_provider.py`
- Validator/critic：`backend/agent/judge_router.py`
- Resume parser：`backend/services/resume_parser.py`
- Speech analyzer：`backend/services/speech_analyzer.py` + `audio_processor.py`
- Expression analyzer：`backend/services/expression_analyzer.py`
- Report synthesizer：`backend/services/report_generator.py` + `llm_provider.py`（`generate_deep_report_analysis`）
- Topic planner：`backend/services/llm_provider.py`（`suggest_next_topic_llm`）

## 9. 前端交互与可视化映射

### 论文位置
- 实现与界面：`sec:implementation`（UI 与部署）

### 代码位置
- 面试页面：`app/pages/4_Interview.py`
- 报告页面：`app/pages/5_Report.py`
- 头像数字人：`app/components/avatar.py`
- 视频采集组件：`app/components/expression_video.py` + `video_capture_component.py` + frontend html

说明：聊天流程、thinking 日志、评估展示、音视频采集都在页面层完成，并调用后端服务。

## 10. 参数与配置映射

### 论文位置
- 参数表：`tab:algorithm_parameters`

### 代码位置
- 配置中心：`backend/core/config.py`
  - 轮次边界相关参数
  - selector strategy
  - LLM 开关与模型
  - 多评审数量
  - agent feature flags

## 11. 实验与复现映射

### 论文位置
- `sec:experiments` / `sec:results`

### 代码与产物位置
- 复现脚本与结果口径（论文中引用）：`reproduce_results/*`（按论文描述）
- 报告数据来源：数据库中的 `Evaluation` / `AskedQuestion` / `Report`

说明：论文强调了“模拟数据/占位数据”的边界，实际协作时应优先替换为真实数据并重算图表。

---

## 快速核对清单（提交前）

- 论文每个“方法子节”是否都能在代码中找到主模块？  
- 论文提到的“回退机制”是否在代码中可触发？  
- 参数表中的关键参数是否都在 `config.py` 可配置？  
- Results 中数字是否和复现脚本输出一致？  

如果你希望，我可以继续把这份映射再细化成“章节段落 -> 函数名 -> 关键参数 -> 测试点”的四列表格版，方便逐条对稿。

