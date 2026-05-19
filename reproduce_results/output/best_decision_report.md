# Best Decision Report

- Generated at: `2026-05-18 09:39:54Z`
- Decision: `GO`
- Recommended rollout stage: `10%`
- Gate reason: `all_passed`

## Best Configuration

- Reward weights: `alpha=0.05`, `beta=0.05`, `gamma=0.05`
- Width policy: `avg_width=1.0`, `top1_width_match=100.0%`
- Subtask policy: `action_diversity=1`

## Canary Delta at Recommended Stage

- Quality delta: `12.38%`
- Cost delta: `0.0%`
- P95 latency delta: `0.0%`
- Fallback delta: `0.0%`

## Reproducibility

- Snapshot rows: `1227`
- Key artifacts:
  - `tab_training_snapshot.csv`
  - `tab_eval_policy_ablation.csv`
  - `tab_eval_policy_reward_sweep.csv`
  - `tab_width_policy.csv`
  - `tab_subtask_policy.csv`
  - `tab_canary_abtest.csv`
  - `tab_go_nogo.csv`
  - `tab_best_config.csv`
