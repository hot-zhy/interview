"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Database (default: SQLite for easy deployment; override with MySQL in .env)
    database_url: str = "sqlite:///data/interview.db"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    
    # LLM (Optional)
    zhipuai_api_key: Optional[str] = None
    zhipuai_model: str = "glm-4-flash"
    llm_use_cot: bool = False  # whether to enable CoT-style reasoning in evaluator prompt
    llm_multi_judge_count: int = 1  # 1 means single judge; >1 enables multi-judge aggregation
    llm_multi_judge_parallel_enabled: bool = True
    llm_multi_judge_max_parallel: int = 4
    llm_multi_judge_timeout_sec: float = 25.0
    llm_multi_judge_fail_open_min_results: int = 1
    
    # App Settings
    app_name: str = "AI Interview System"
    debug: bool = False
    
    # Track & Chapter mapping
    track_chapters: dict = {
        "Java Backend": {
            "Java基础": 0.15,
            "集合": 0.15,
            "并发": 0.20,
            "JVM": 0.15,
            "Spring": 0.15,
            "数据库": 0.10,
            "系统设计": 0.10,
        },
        "Java Concurrency": {
            "并发": 0.40,
            "Java基础": 0.20,
            "JVM": 0.20,
            "系统设计": 0.20,
        },
        "JVM & Performance": {
            "JVM": 0.50,
            "并发": 0.20,
            "Java基础": 0.15,
            "系统设计": 0.15,
        },
        "Spring & Microservices": {
            "Spring": 0.40,
            "系统设计": 0.25,
            "数据库": 0.20,
            "Java基础": 0.15,
        },
    }

    # Adaptive algorithms (config flags; keep backward compatible defaults)
    difficulty_strategy: str = "heuristic"  # "heuristic" | "target_score_control"
    target_score: float = 0.70  # desired average score for difficulty control
    difficulty_step: float = 1.0  # max step per update (in difficulty levels)
    difficulty_kp: float = 1.2  # proportional gain for control update
    difficulty_kd: float = 0.6  # trend gain (derivative-like)

    selector_strategy: str = "personalized"  # "weighted_random" | "thompson_sampling" | "personalized" | "contextual_bandit"
    personalized_exploration_rate: float = 0.15  # 个性化选题时的随机探索率（避免过于贪婪）
    thompson_alpha0: float = 1.0
    thompson_beta0: float = 1.0
    success_threshold: float = 0.70  # success if overall_score >= threshold
    recent_chapter_avoid_k: int = 2  # avoid last k chapters when possible
    thompson_context: str = "chapter_difficulty"  # "chapter" | "chapter_difficulty"
    # Agentic-RL (question-selection module) defaults
    rl_target_module: str = "question_selection"
    rl_policy_artifact_path: str = "reproduce_results/output/contextual_bandit_policy.json"
    rl_bandit_alpha: float = 0.35
    rl_feature_window: int = 3
    rl_reward_gain_weight: float = 0.40
    rl_reward_quality_weight: float = 0.25
    rl_reward_coverage_weight: float = 0.20
    rl_reward_cost_weight: float = 0.15
    rl_cost_llm_penalty: float = 0.05
    rl_cost_followup_penalty: float = 0.03
    # Agentic-RL (evaluation-routing module) defaults
    enable_eval_policy_agent: bool = True
    eval_policy_strategy: str = "contextual_bandit"  # "heuristic" | "contextual_bandit"
    eval_policy_artifact_path: str = "reproduce_results/output/contextual_eval_policy.json"
    eval_policy_alpha: float = 0.25
    eval_policy_max_llm_calls_per_session: int = 8
    eval_policy_max_multi_judge_per_session: int = 3
    eval_reward_agreement_weight: float = 0.45
    eval_reward_quality_weight: float = 0.25
    eval_reward_feedback_weight: float = 0.20
    eval_reward_cost_weight: float = 0.10
    eval_cost_llm_penalty: float = 0.03
    eval_cost_multi_judge_penalty: float = 0.07
    eval_cost_followup_penalty: float = 0.02
    eval_reward_latency_weight: float = 0.10
    eval_reward_instability_weight: float = 0.10
    eval_latency_budget_ms: float = 3500.0
    eval_instability_reference: float = 0.25

    # Joint reward weighting for offline sweeps.
    joint_reward_quality_weight: float = 1.0
    joint_reward_cost_alpha: float = 0.15
    joint_reward_latency_beta: float = 0.10
    joint_reward_instability_gamma: float = 0.08
    
    # 面试结束与轮次
    min_rounds_ratio: float = 0.5   # 最少轮次 = total_rounds * min_rounds_ratio
    max_rounds_ratio: float = 1.2   # 最多轮次 = total_rounds * max_rounds_ratio（可略超用户设置）
    max_rounds_cap: int = 20        # 轮次绝对上限

    # Agentic framework feature flags (all default OFF to preserve legacy behaviour)
    enable_agent_controller: bool = True
    enable_memory_state: bool = False
    enable_tool_routing: bool = True
    enable_multi_judge: bool = True
    enable_followup_planner: bool = True
    enable_agent_tracing: bool = True

    # WideSeek-style rollout & guardrails
    enable_wide_subtask_planner: bool = True
    wide_subtask_max_workers: int = 3
    rollout_variant: str = "wideseek_w2"  # control | wideseek_w2 | wideseek_w4 | wideseek_w8
    rollout_percent: int = 100
    rollout_hash_salt: str = "wideseek-r1-rollout"
    guardrail_max_llm_calls_per_session: int = 10
    guardrail_max_multi_judge_per_session: int = 4
    guardrail_max_fallback_rate: float = 0.5
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

