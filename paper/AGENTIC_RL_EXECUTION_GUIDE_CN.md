

| Agent RL 概念 | 你的系统对应                                       |
| ------------- | -------------------------------------------------- |
| State         | 当前轮次、回答长度、近窗得分、缺失知识点、预算消耗 |
| Action        | rule、llm_single、llm_multi、followup              |
| Reward        | 评分一致性、反馈命中、报告质量、成本惩罚           |
| Environment   | 面试会话 / 题库 / 候选人回答 / 评分器              |
| Policy        | 评估路由策略                                       |
| Trajectory    | 一场完整面试的出题-回答-评估序列                   |

> 如何把 Agent 工作流形式化为 MDP / Bandit，并设计 state、action、reward、fallback、offline evaluation。



## RL 基础

| 概念                       | 为什么重要                             |
| -------------------------- | -------------------------------------- |
| MDP / POMDP                | Agent 多轮决策的数学建模基础           |
| State / Action / Reward    | 你的系统设计核心                       |
| Policy                     | 策略如何选择动作                       |
| Value / Q-value            | 如何评估某个动作长期是否划算           |
| Exploration / Exploitation | 什么时候尝试新策略，什么时候用稳定策略 |
| Contextual Bandit          | 非常适合你的评估路由策略               |
| Policy Gradient / PPO      | 理解 LLM RL 后训练的基础               |
| Offline Policy Evaluation  | 用历史日志验证新策略，避免直接线上试错 |

**推荐资料：**

| 资料                                                      | 适合程度         | 用法                                        |
| --------------------------------------------------------- | ---------------- | ------------------------------------------- |
| Sutton & Barto《Reinforcement Learning: An Introduction》 | 经典基础         | 看第 1、2、3、5、6、13 章即可               |
| OpenAI Spinning Up                                        | 工程入门         | 看 Key Concepts、Policy Gradient、PPO       |
| LinUCB 论文                                               | 和你的项目最贴近 | 理解 Contextual Bandit 如何根据上下文选动作 |

Sutton & Barto 是强化学习最经典教材；OpenAI Spinning Up 对 PPO 和策略优化讲得比较工程化；LinUCB 是 Contextual Bandit 经典方法，曾用于个性化推荐中的上下文动作选择，和你“根据面试状态选择评估动作”的问题非常接近。

------

## 阶段二：LLM 后训练 RL

这部分主要理解：

```
SFT → RLHF / RLAIF → PPO / DPO / GRPO → Reasoning RL → Agent RL
```

你需要重点看：

| 概念              | 解释                                                         |
| ----------------- | ------------------------------------------------------------ |
| PPO               | 最经典的 RLHF 算法之一                                       |
| GRPO              | **DeepSeek-R1** 类推理模型常用的 group-based policy optimization 思路 |
| Reward Model      | 训练模型判断输出好坏                                         |
| Outcome Reward    | 只看最终答案对错                                             |
| Process Reward    | 看中间推理步骤是否合理                                       |
| Sparse Reward     | 只有最后成功/失败反馈                                        |
| Credit Assignment | 多步 Agent 中，如何判断是哪一步导致成功/失败                 |

对于 Agent RL 来说，**credit assignment** 特别关键。因为 Agent 可能经历：

```
思考 → 调工具 → 观察结果 → 再思考 → 再调工具 → 最终回答
```

最终成功了，不代表每一步都好；最终失败了，也不代表每一步都错。这就是 Agent RL 难的地方。

------

# Agent RL 论文

## Survey

### 1. The Landscape of Agentic Reinforcement Learning for LLMs: A Survey

[[2509.02547\] The Landscape of Agentic Reinforcement Learning for LLMs: A Survey](https://arxiv.org/abs/2509.02547)

这篇是目前最适合作为入口的综述。它把 Agentic RL 和传统 LLM-RL 区分开：传统 LLM-RL 更像单步 MDP，而 Agentic RL 更接近长时序、多轮交互、部分可观测的 POMDP。论文还整理了 planning、tool use、memory、reasoning、self-improvement、perception 等 Agent 能力维度。

**你可以重点看：**

- Agentic RL 定义；
- MDP / POMDP 建模；
- Agent 能力分类；
- benchmarks 和 environments；
- 未来挑战。

**和你项目的关系：**

你的面试系统可以直接借用它的表述：

> 我们将面试评估 Agent 建模为一个受约束的多轮决策过程，其中策略根据会话状态选择评估动作，并在质量、成本和安全约束之间优化长期收益。

------

## B. 多轮 Agent RL 框架

### 2. RAGEN: Understanding Self-Evolution in LLM Agents via Multi-Turn Reinforcement Learning

RAGEN 是非常值得读的一篇。它提出 StarPO，即 **State-Thinking-Actions-Reward Policy Optimization**，专门研究 LLM Agent 多轮 RL。论文强调，多轮 Agent RL 面临长时序决策、随机环境反馈、稀疏奖励和训练不稳定问题；它还发现如果没有细粒度、reasoning-aware reward，Agent 容易学到浅层策略或产生 hallucinated thoughts。

- StarPO 的 trajectory 结构；
- 多轮 rollout 如何组织；
- reward variance cliff / gradient spike；
- 为什么需要 trajectory filtering；
- 为什么 reward 不能只看最终成功率。

**和你项目的关系：**

你的 `ask_followup_then_eval` 很适合用 RAGEN 的思想解释：

```
State: 当前候选人回答不完整
Thought: 判断是否需要追问
Action: 发起 follow-up
Reward: 追问后评分一致性提升 - 额外轮次成本
```

------

### 3. Agent Lightning: Train ANY AI Agents with Reinforcement Learning

Agent Lightning 是微软提出的 Agent RL 框架。它的核心思想是：**把 Agent 执行逻辑和 RL 训练逻辑解耦**。论文声称可以把 LangChain、OpenAI Agents SDK、AutoGen 或自定义 Agent 接入 RL 训练，而不需要大幅修改原有 Agent 代码。它把 Agent 执行形式化为 MDP，并提出统一数据接口和层次化 RL 算法 LightningRL，用于处理复杂工作流、多 Agent 和动态调用逻辑。

**你可以重点看：**

- Training-Agent Disaggregation；
- 轨迹如何从 Agent runtime 中采集；
- 如何把复杂 Agent 执行拆成 transition；
- credit assignment module；
- Text-to-SQL、RAG、math tool-use 实验。

**和你项目的关系：**

你的项目结构其实很像 Agent Lightning：

```
controller.py        → Agent runtime
eval_policy.py      → policy
judge_router.py     → action executor
export_db.py        → trajectory export
calc_eval_policy.py → offline training
```

你可以把它包装成：

> 我们参考训练-执行解耦思想，将面试 Agent 的在线执行链路与离线策略学习链路分离，通过轨迹导出进行策略优化，并通过策略文件回灌在线系统。

------

## C. Web / Tool-use Agent RL

### 4. WebAgent-R1: Training Web Agents via End-to-End Multi-Turn RL

WebAgent-R1 关注 web agent 的多轮端到端 RL。论文指出，以前很多 LLM RL 主要集中在数学等单轮任务，而 Web Agent 需要在动态网页环境中进行长时序决策，所以需要多轮交互式 RL。

**你可以重点看：**

- 多轮 web interaction；
- online interaction with environment；
- outcome-based reward；
- rollout 采样；
- 长时序决策难点。

**和你项目的关系：**

虽然你的系统不是 Web Agent，但逻辑很像：

```
Web Agent: 观察网页 → 点击/输入 → 得到网页反馈 → 继续操作
Interview Agent: 观察回答 → 评分/追问/换题 → 得到候选人反馈 → 继续面试
```

------

### 5. WebRL: Training LLM Web Agents via Self-Evolving Online Curriculum RL

WebRL 主要解决 web agent 训练中的三个问题：训练任务稀缺、反馈信号稀疏、在线学习中的策略分布漂移。它采用 self-evolving curriculum，让 Agent 在训练中不断生成或调整任务难度。

**你可以重点看：**

- self-evolving curriculum；
- sparse feedback；
- policy distribution drift；
- 任务难度如何动态调整。

**和你项目的关系：**

你的出题策略也可以借鉴 curriculum 思想：

```
候选人表现稳定 → 提高题目难度
候选人某章节薄弱 → 增加该章节覆盖
候选人回答不完整 → 先追问再进入下一题
```

------

### 6. DynaWeb: Model-Based Reinforcement Learning of Web Agents

DynaWeb 是 2026 年的新工作，方向是 **model-based RL for web agents**。它强调用学习到的 world model 降低真实环境交互成本和风险，这对 Agent RL 很重要，因为真实网页/真实用户环境中直接在线试错成本很高。

**你可以重点看：**

- model-based RL；
- world model；
- 如何减少真实环境试错；
- 训练效率和安全性。

**和你项目的关系：**

你的面试系统也不能直接在线乱试，所以可以先做：

```
历史会话轨迹 → 离线环境模拟 → 策略回放评估 → 小流量灰度
```

这就是一种轻量版 model-based / offline evaluation 思路。

------

## D. 工具使用 / 推理 Agent

### 7. Agent-R1: Training Powerful LLM Agents with End-to-End RL

Agent-R1 研究多轮推理和工具调用场景中的端到端 RL。论文描述的轨迹结构包括多轮 reasoning、tool-based actions、environment feedback，并把工具响应追加到下一步状态中。

**你可以重点看：**

- tool call trajectory；
- 多跳问答中的搜索工具使用；
- RL 算法在多轮交互任务中的效果；
- action-feedback-next state 的组织方式。

**和你项目的关系：**

你的评估路由也可以抽象成 tool-use：

```
rule_judge 是工具
llm_judge 是工具
multi_judge 是工具
followup_generator 是工具
```

策略学的是：

> 当前状态下调用哪个工具最划算。

------

### 8. Tool-R1: Sample-Efficient Reinforcement Learning for Tool Use

Tool-R1 关注工具调用能力的样本效率。它属于 **tool-use RL** 方向，适合你理解“如何让模型学会什么时候调用工具、怎么调用工具”。

**和你项目的关系：**

你可以把评估器看成一组工具：

```
rule_only
llm_single
llm_multi
retrieval_check
followup
```

Agent RL 的目标就是学习 tool routing。

------

### 9. Reinforcing Multi-Turn Reasoning in LLM Agents via RL

这篇关注多轮工具使用场景中的推理增强，并明确把 multi-turn tool-use 建模为 MDP。它很适合用来支撑你论文中“面试评估是一个多轮决策过程”的表述。





![image-20260424182732960](C:\Users\10205\AppData\Roaming\Typora\typora-user-images\image-20260424182732960.png)









[[2602.04634\] WideSeek-R1: Exploring Width Scaling for Broad Information Seeking via Multi-Agent Reinforcement Learning](https://arxiv.org/abs/2602.04634)

### WideSeek-R1: Exploring Width Scaling for Broad Information Seeking via Multi-Agent Reinforcement Learning 2026

它不是让一个 Agent 独自完成复杂搜索任务，而是让一个 **Lead Agent 负责拆任务和汇总**，多个 **Subagents 并行查资料/执行子任务**，最后用 **GRPO 类似的多智能体强化学习方法** 来训练整个系统，让它学会更好地分工、搜索、汇总和回答。

![image-20260424180900773](C:\Users\10205\AppData\Roaming\Typora\typora-user-images\image-20260424180900773.png)



Lead 和 Subagent 共享同一个底座模型参数（shared LLM weights），只隔离上下文，不隔离权重。

所以流程是：

- Rollout 时：Lead / Subagent 虽然是不同“角色实例”，但前向都走同一套参数 θ。

- Train 时：

把所有角色产生的 token loss（经过 agent/token 两层加权）汇总成一个总 loss：

![image-20260429091806233](C:\Users\10205\AppData\Roaming\Typora\typora-user-images\image-20260429091806233.png)

- 反向传播得到 ∇θL，更新一次共享参数 θ←θ−η∇θ

- Sync Param（图里紫色箭头）：下一轮 Rollout 启动时，Lead 和所有 Subagent 都加载这份新参数；因此看起来像“梯度更新到了所有 Agent”。



![image-20260429092416503](C:\Users\10205\AppData\Roaming\Typora\typora-user-images\image-20260429092416503.png)

![image-20260429093155041](C:\Users\10205\AppData\Roaming\Typora\typora-user-images\image-20260429093155041.png)

![image-20260429093201611](C:\Users\10205\AppData\Roaming\Typora\typora-user-images\image-20260429093201611.png)







在强化学习里，**rollout** 指的是：

> 让当前策略实际跑一遍任务，生成一条完整轨迹，用来计算奖励和训练。

```
用户问题
→ Lead Agent 拆解任务
→ 多个 Subagent 并行执行子任务
→ Subagent 返回结果
→ Lead Agent 汇总
→ 继续迭代
→ 最终生成 Answer
```

------

##  Query

图里例子是：

```
List Harwards universities with their name, city, and founding year.
```

也就是：

> 列出常春藤学校的名字、城市和创办年份。

这是一个 **广域信息搜索任务**，因为它不是查一个事实，而是要查多个对象的多个属性。

------

## Lead Agent：主 Agent

图里的 **Lead Agent** 负责：

```
理解问题
拆解子任务
分配任务
接收子 Agent 结果
判断是否继续搜索
最终汇总答案
```

比如它把任务拆成：

```
查 Harvard 的位置和创办年份
查 Princeton 的位置和创办年份
查 Yale 的位置和创办年份
```

所以 Lead Agent 更像是：

> 总控、规划器、调度器、汇总器。

------

subagent可以并行执行，比如调用：

```
搜索工具
网页工具
文档工具
数据库工具
```

------

## Responses：子 Agent 返回结果

图中返回了：

```
Harvard is in Cambridge, MA, founded in 1636.
Princeton is in Princeton, NJ, founded in 1746.
Fail to retrieve location and year for Yale.
```

也就是说，有的子任务成功，有的失败。

Lead Agent 接收这些结果后，会继续判断：

```
信息是否完整？
是否需要重新查？
是否需要换一个子 Agent？
是否可以汇总最终答案？
```



------

# Train 

图的下半部分是 **训练过程**。

它用的是类似 **GRPO** 的强化学习训练。

简单说：

> 系统先让多个 Agent 跑出一组答案，然后根据最终答案质量计算奖励，再反向更新 Agent 的参数，让以后分工和回答更好。

------

# GRPO Loss 

图左下角有：

```
GRPO Loss
Update Param
```

GRPO 可以理解成：

> 不用单独训练 value model，而是对同一个问题采样一组回答，然后比较这组回答的好坏，用**相对优势**来更新模型。

```
同一道题，让模型生成 G 个答案
每个答案得到一个 reward
把这一组 reward 做归一化
好于组内平均的答案被强化
差于组内平均的答案被削弱
```

------

# Group Norm 

图右下角有：

```
Group Norm
R1 ... RG
```

这表示对一组 rollout 的 reward 做归一化。

例如同一个 query 跑了 4 组结果：

| 轨迹         | Reward |
| ------------ | ------ |
| Trajectory 1 | 0.9    |
| Trajectory 2 | 0.7    |
| Trajectory 3 | 0.4    |
| Trajectory 4 | 0.2    |

直接用 reward 训练会不稳定，所以要做 group normalization：

```
看每条轨迹相对于这一组平均水平的好坏
```

最后得到 advantage：

```
A1, A2, ..., AG
```

也就是每条轨迹的“相对优势”。

------

# Multi-Agent Adv Assignment 

图里有：

```
Multi-Agent Adv Assignment
```

这一步很关键。

因为最终答案是多个 Agent 合作完成的，那么问题来了：

> 最终答案好，是谁的功劳？
>  最终答案差，是哪个 Agent 的问题？

这就是多智能体强化学习里的 **credit assignment** 问题。

举个例子：

```
Subagent 1 查 Harvard 查对了
Subagent 2 查 Princeton 查对了
Subagent 3 查 Yale 查错了
Lead Agent 最后汇总时也没发现错误
```

最终答案 reward 不高。

那训练时不能简单地让所有 Agent 都被同样惩罚，而要尽量判断：

```
哪个子 Agent 贡献大？
哪个子 Agent 出错？
Lead Agent 有没有正确汇总？
```

所以 Multi-Agent Advantage Assignment 就是：

> 把整体 reward 分配给不同 Agent，让每个 Agent 得到更合理的训练信号。

------

# Dual-Level Adv Reweighting 

图里还有：

```
Dual-Level Adv Reweighting
Agent-Level
Token-Level
```

这表示优势权重不只在一个层级上分配，而是在两个层级上分配：

| 层级            | 含义                                     |
| --------------- | ---------------------------------------- |
| **Agent-Level** | 哪个 Agent 的整段行为更应该被奖励或惩罚  |
| **Token-Level** | 这个 Agent 生成的哪些 token / 动作更关键 |

也就是说，它不是粗暴地说：

```
Subagent 1 整体 +1
Subagent 2 整体 -1
```

而是更细：

```
Subagent 1 的某些搜索步骤很有用
Subagent 2 的某些回答片段导致错误
Lead Agent 的某个汇总判断有问题
```

这样训练信号会更细粒度。

------

# Sync Param

图中有两处：

```
Sync Param
Update Param
```

这表示训练后的参数会同步给 rollout 阶段的 Agent。

也就是：

```
rollout 生成轨迹
→ 计算 reward
→ 计算 GRPO loss
→ 更新参数
→ 把新参数同步给 Lead Agent / Subagents
→ 下一轮 rollout 用更新后的策略
```

这个过程就是强化学习训练循环。

------



```
1. 用户提出复杂查询

2. Lead Agent 拆解任务

3. 多个 Subagents 并行执行子任务

4. 每个 Subagent 调用搜索/文档等工具

5. Subagents 返回局部答案

6. Lead Agent 聚合结果，必要时继续分配任务

7. 最终生成 Answer

8. 系统根据 Answer 质量计算 group reward

9. 对 reward 做 group normalization

10. 把 advantage 分配给不同 Agent 和不同 token

11. 用 GRPO loss 更新参数

12. 同步参数，进入下一轮训练
```

------

# ReAct Agent 

普通 ReAct 更像：

```
Thought → Action → Observation → Thought → Action → Observation
```

通常是一个 Agent 自己循环。

WideSeek-R1 更像：

```
Lead Agent 规划
→ 多个 Subagents 并行行动
→ Lead Agent 汇总
→ 多智能体 RL 训练协作策略
```

所以区别是：

| 维度       | ReAct              | WideSeek-R1                |
| ---------- | ------------------ | -------------------------- |
| Agent 数量 | 通常单 Agent       | Lead Agent + 多 Subagents  |
| 搜索方式   | 串行为主           | 并行为主                   |
| 核心能力   | 推理 + 工具调用    | 任务拆解 + 并行搜索 + 协作 |
| 训练方式   | 多数不一定 RL 训练 | MARL + GRPO                |
| 适用任务   | 一般工具调用任务   | 广域信息搜索任务           |

# 

| WideSeek-R1    | 面试系统                                           |
| -------------- | -------------------------------------------------- |
| Query          | 一场面试目标：评估候选人能力                       |
| Lead Agent     | 面试 Controller / Planner                          |
| Subagents      | 评分 Agent、追问 Agent、题目选择 Agent、报告 Agent |
| Subtasks       | 评估回答、识别缺失点、选择下一题、生成报告         |
| Reward         | 评分一致性、gap 命中、报告质量、成本控制           |
| Group Training | 多策略对比、trajectory-level reward                |

[arxiv.org/pdf/2501.12948](https://arxiv.org/pdf/2501.12948)





### 11. Agentic Reinforcement Learning for Real-World Code Repair

这篇研究真实代码修复任务中的 Agentic RL。它在 VerL 内使用多个并发代码修复 Agent，并尝试 PPO 和 GRPO，最终采用 GRPO 做主要实验。

**和你项目的关系：**

如果你的面试系统包含代码题评估，这篇可以参考：

- 如何用测试用例作为 reward；
- 如何把 validate/build 结果作为环境反馈；
- 如何处理高并发 rollout 的资源竞争。

------

# 4. 工程框架推荐

## 1. RAGEN

适合研究 **multi-turn Agent RL**。它支持 PPO、GRPO，也支持多轮 online RL training。你可以用它理解 Agent rollout、trajectory、reward 和训练诊断。

适合你做：

```
面试环境 Gym 化
多轮出题 / 追问 / 评分轨迹训练
```

------

## 2. Agent Lightning

适合研究 **如何把已有 Agent 系统接入 RL**。如果你已经有 LangGraph / controller / judge_router 这种工程结构，Agent Lightning 的“执行-训练解耦”思想非常值得学。

适合你做：

```
已有面试 Agent 不大改代码
导出轨迹
离线训练 policy
再部署策略文件
```

------

## 3. verl

verl 是现在很多 LLM RL 训练会用到的工程框架，支持 PPO 等算法，也被用于大模型后训练和多轮 Agent RL 场景。Google Cloud 2026 年还发布了使用 Ray 和 verl 在 GKE 上做分布式 RL 训练的教程，说明这类框架正在走向更工程化部署。

适合你做：

```
PPO / GRPO 训练实验
LLM 后训练
分布式 rollout
```
