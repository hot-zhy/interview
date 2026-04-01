# AI 面试系统论文说明（导师汇报 2 页版）

> 对应论文：`interview/paper/main.tex`  
> 目标：用最短路径讲清楚“这篇论文在做什么、为什么合理、系统如何落地、结果怎么看”。

## 1. 这篇论文到底在做什么

这篇论文把技术面试定义为一个**受限动作空间的序列决策问题**，核心不是“让大模型自由发挥”，而是构建一个可审计、可回退的 agentic 编排框架。

- 闭环：`Observation -> Memory -> State -> Policy -> Action -> Tool -> Feedback`
- 受限动作：`ask-next / follow-up / terminate`
- 核心目标：在有限题量内尽快校准难度、精准选题、稳定评估并生成可解释报告

一句话总结：  
**这是一个 memory-aware、tool-augmented、reliability-constrained 的面试智能体框架，而不是开放式自治 Agent。**

## 2. 三个研究问题（RQ）与五个贡献（C）

### RQ
- **RQ1**：如何在有限题量下快速且稳定地做难度校准与终止决策？
- **RQ2**：如何把缺口、简历先验、覆盖率、评估反馈统一到选题策略？
- **RQ3**：如何兼顾规则评分稳定性与 LLM 语义理解能力，并具备可靠回退？

### C1–C5
- **C1**：提出 OMPA 闭环的 memory-aware agentic 面试框架
- **C2**：状态感知自适应控制（难度更新 + 终止）
- **C3**：状态感知多目标选题（含 LLM topic planner + priority cascade）
- **C4**：可靠性约束混合评审（routing + validator + fallback + optional multi-judge）
- **C5**：工具化架构（包含多步 agentic 报告生成）

## 3. 系统设计（工程视角）

### 3.1 三层架构
- **展示层**：Streamlit 页面（题目交互、语音视频、报告）
- **业务层**：Controller、Question Selector、Hybrid Judger、Follow-up Planner、Report Synthesizer
- **数据层**：SQLAlchemy 持久化会话、题目、评分、报告与状态

### 3.2 为什么是“工具编排”而不是“单模型端到端”
- 各能力拆成专用工具，降低耦合、便于验证与替换
- 每个工具都定义 fallback，LLM 不可用时不中断流程
- 控制逻辑确定性强，可复现、可审计

## 4. 算法主干（按面试流程讲，易懂版）

### 4.1 会话初始化与首题
- **输入**：岗位方向、初始难度、目标轮数、可选简历解析
- **怎么做**：有简历且 LLM 可用时先生成个性化首题；否则回退题库选题
- **怎么评估**：首题相关度（和岗位/简历是否匹配）、首题可答性、首轮可用率

### 4.2 Observation -> Memory -> State（每轮更新）
- **输入**：本轮题目、候选人回答、评估结果（含 missing points / next-direction）
- **怎么做**：先记录 observation，再更新 memory（分数轨迹、覆盖、缺口、追问计数），最后压缩成 state 供决策
- **怎么评估**：跨轮一致性、状态利用率（hint 是否被后续选题采用）、可追踪性

### 4.3 回答评估（RQ3：Hybrid Judging）
- **输入**：题目 + 标准答案 + 用户回答
- **怎么做**：
  1) Rule judge 先给稳定基线  
  2) LLM judge 做语义增强  
  3) Validator 校验结构和范围  
  4) 失败自动 fallback 到 rule
- **怎么评估**：agreement（kappa/ICC/exact）、非法输出率、回退成功率、uptime

### 4.4 自适应控制（RQ1：难度与终止）
- **输入**：历史分数、难度轨迹、章节覆盖、剩余预算
- **怎么做**：
  - 难度更新：`heuristic` 或 `target-score-control`
  - 终止判断：最少轮次约束 + 优秀提前结束/低分提前结束/覆盖稳定结束 + 预算上限
- **怎么评估**：calibration、convergence、stability（目标口径：4-5 题内稳定）

### 4.5 追问策略（Follow-up）
- **输入**：本题得分区间、missing points、追问次数、剩余预算
- **怎么做**：先判断“要不要追问”；需要时优先上下文 LLM 追问，不可用时模板回退
- **怎么评估**：追问有效率、追问后得分提升、重复追问率

### 4.6 下一题选择（RQ2：State-Aware Selection）
- **输入**：缺口集合、简历先验、覆盖状态、next-direction、当前难度
- **怎么做**：`LLM topic planner + priority cascade`
  - Priority 0：LLM 建议章节（需校验）
  - Priority 1：缺口优先（含 next-direction 注入）
  - Priority 2：简历匹配
  - Priority 3：覆盖探索（weighted random / Thompson / UCB）
  - 个性化模式：ability estimation + Fisher 信息
- **怎么评估**：gap targeting、coverage、personalization relevance

### 4.7 终止与报告生成
- **输入**：全会话轨迹（题目、分数、缺口、难度/章节轨迹、可选语音表情信号）
- **怎么做**：多步报告合成（综合总结、维度分析、缺口根因、学习计划、策略轨迹）
- **怎么评估**：报告可解释性、建议可执行性、用户满意度

## 5. 结果怎么讲（避免过度 claim）

### 5.1 结果口径
- RQ1：看 calibration、convergence、稳定性
- RQ2：看 gap targeting、coverage、personalization relevance
- RQ3：看 agreement（kappa/ICC）与 uptime（含回退）

### 5.2 当前版本注意点
- 论文已明确部分数据是 illustrative/synthetic 与复现实验口径
- 汇报时要强调“机制已实现、数据仍可继续补强”

## 6. 你可以怎么讲给导师听

推荐 90 秒版本（按系统顺序）：

1. **初始化**：先用简历和岗位信息定首题，LLM 不可用就回退题库。  
2. **每轮闭环**：回答先评估，再更新 memory/state，控制器决定“追问/下一题/结束”。  
3. **评估可靠**：rule 保底、LLM 增强、validator 校验、异常自动 fallback。  
4. **选题自适应**：优先补缺口，再看简历与覆盖，并结合探索策略防止偏科。  
5. **结果价值**：在有限题量内更快校准、更准选题、更稳评估，且全流程可审计可回退。  

---

如果你需要，我还可以再给你一版“答辩 Q&A 备忘清单”（例如“为什么不是端到端 LLM？”“为什么说 agentic 但又受限？”“如何证明可靠性？”）。

