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

## 4. 算法主干（按论文 Section 3）

### 4.1 RQ1：Adaptive Control
- 基于用户目标轮数推导 `n_min/n_max`
- 用滑窗统计（均值、近窗均值、方差）监控状态
- 四类终止条件：优秀提前结束、低分提前结束、稳定覆盖结束、预算耗尽
- 难度更新支持两种策略：heuristic / target-score-control
- 关键结论口径：**4–5 题内达到稳定校准**

### 4.2 RQ2：State-Aware Selection
- 理论上是多目标优化（Gap、Resume、Coverage、Info、Explore、NextDir）
- 实现上采用“LLM topic planner + priority cascade”
  - Priority 0：LLM 建议下一个 chapter（需验证）
  - Priority 1：缺口优先（含 next-direction 反馈注入）
  - Priority 2：简历匹配
  - Priority 3：覆盖探索（weighted random / Thompson / UCB）
- 个性化模式引入 IRT-inspired ability estimation + Fisher 信息

### 4.3 Follow-up 策略
- 不把追问当“随机追加”，而是一个显式动作
- 由分数区间、missing points、重复性检测、每题追问预算共同触发
- LLM 可用时做上下文追问，不可用时模板回退

### 4.4 RQ3：Hybrid Judging
- Rule-based judge 给稳定基线
- LLM judge 给语义细粒度补充
- Validator 校验结构与取值范围
- Fallback Router 保证异常时回退规则评分
- 可选 multi-judge 聚合降低波动

## 5. 结果怎么讲（避免过度 claim）

### 5.1 结果口径
- RQ1：看 calibration、convergence、稳定性
- RQ2：看 gap targeting、coverage、personalization relevance
- RQ3：看 agreement（kappa/ICC）与 uptime（含回退）

### 5.2 当前版本注意点
- 论文已明确部分数据是 illustrative/synthetic 与复现实验口径
- 汇报时要强调“机制已实现、数据仍可继续补强”

## 6. 你可以怎么讲给导师听

推荐 3 分钟版本：

1. **先立问题**：固定面试不公平、随机选题不高效、纯规则/纯LLM评估各有硬伤。  
2. **再讲框架**：我们把面试建模成受限动作的闭环系统，核心是 memory + policy + tool routing。  
3. **最后讲价值**：在有限题量里更快校准、更准选题、更稳评估，而且任何 LLM 故障都可自动降级。  

---

如果你需要，我还可以再给你一版“答辩 Q&A 备忘清单”（例如“为什么不是端到端 LLM？”“为什么说 agentic 但又受限？”“如何证明可靠性？”）。

