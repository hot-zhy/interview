# Agentic-RL 面试评估与出题执行文档

## 1. 实施目标
- 主线：将面试评估从固定路由升级为可学习策略（rule / llm_single / llm_multi / followup_then_eval）。
- 副线：将章节选择策略从单轮收益扩展到会话长期收益（含终局质量奖励）。
- 安全约束：策略不可用、输出非法、预算超限时必须自动回退，不影响主流程可用性。

## 2. 已落地模块映射
- 评估策略定义：`backend/agent/eval_policy.py`
- 在线路由与回退：`backend/agent/judge_router.py`
- Agent 控制器接入：`backend/agent/controller.py`
- 轨迹导出：`scripts/export_db.py`（新增 `eval_policy_trajectory.csv`）
- 评估策略离线训练：`reproduce_results/eval_policy_utils.py`、`reproduce_results/calc_eval_policy.py`
- 出题策略会话奖励扩展：`backend/services/selection_rl.py`、`reproduce_results/bandit_utils.py`
- 联合消融：`reproduce_results/calc_joint_ablation.py`

## 3. 评估主线 MDP（可直接写入论文）
- State：轮次比例、回答长度、近窗得分、缺失点数量、fallback计数、LLM预算消耗、多评审消耗。
- Action：`rule_only` / `llm_single` / `llm_multi` / `ask_followup_then_eval`。
- Reward：一致性 + 质量 + 反馈命中 - 成本惩罚（LLM、多评审、追问）。
- Constraints：最大LLM调用次数、最大multi-judge次数、异常强制回退。

## 4. 训练与验证流程
1. 导出数据  
   - `python scripts/export_db.py --output data/`
2. 训练章节策略与评估路由策略  
   - `python reproduce_results/reproduce.py --data-dir data`
3. 关键产物  
   - `reproduce_results/output/contextual_bandit_policy.json`
   - `reproduce_results/output/contextual_eval_policy.json`
   - `reproduce_results/output/tab_joint_ablation.csv`

## 5. 在线灰度建议
- 在 `.env` 中配置：
  - `ENABLE_AGENT_CONTROLLER=true`
  - `ENABLE_EVAL_POLICY_AGENT=true`
  - `EVAL_POLICY_STRATEGY=contextual_bandit`
  - `EVAL_POLICY_ARTIFACT_PATH=reproduce_results/output/contextual_eval_policy.json`
- 小流量开启后，重点监控：
  - `rule_fallback` 比例
  - 每会话 LLM 调用次数
  - 评分延迟和失败率
  - 用户满意度变化

## 6. 实验表建议
- `tab_eval_policy.csv`：评估策略训练样本量、平均奖励、平均遗憾、Top1动作匹配率。
- `tab_bandit_policy.csv`：章节策略收益与遗憾。
- `tab_joint_ablation.csv`：Baseline / Eval-RL / Question-RL / 双策略 的对比。

## 7. Demo 脚本建议
- 固定同一候选人会话回放，展示：
  1) Baseline 路由动作序列  
  2) Eval-RL 路由动作序列  
  3) Question-RL 章节选择变化  
  4) 双策略联合下最终报告差异
