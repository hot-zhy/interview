"""Resume-track matching: check if resume skills align with selected job track."""
from typing import List, Tuple, Optional

# Track -> skill keywords that indicate a match (resume should have at least MIN_MATCH_COUNT)
TRACK_SKILL_KEYWORDS = {
    "Java Backend": [
        "Java", "Spring", "Spring Boot", "SpringBoot",
        "MySQL", "PostgreSQL", "Redis", "MongoDB",
        "并发", "多线程", "JVM", "微服务", "分布式",
        "集合", "数据结构", "设计模式",
    ],
    "Java Concurrency": [
        "Java", "并发", "多线程", "JVM",
        "微服务", "分布式", "锁", "线程",
    ],
    "JVM & Performance": [
        "Java", "JVM", "并发", "多线程",
        "微服务", "分布式", "性能", "调优",
    ],
    "Spring & Microservices": [
        "Java", "Spring", "Spring Boot", "SpringBoot",
        "微服务", "分布式", "MySQL", "Redis",
        "Docker", "Kubernetes", "K8s",
    ],
    "AI Agent Engineer": [
        "Agent", "AI Agent", "LangChain", "LangGraph", "AutoGen",
        "Function Calling", "Tool Calling", "工具调用", "MCP",
        "RAG", "Prompt", "LLM", "OpenAI", "智谱", "ZhipuAI",
        "向量数据库", "Milvus", "FAISS", "Qdrant", "评测",
    ],
    "LLM Application Engineer": [
        "LLM", "大模型", "Prompt", "提示词", "RAG",
        "Embedding", "向量", "Function Calling", "OpenAI",
        "LangChain", "LangGraph", "智谱", "ZhipuAI", "Claude",
        "评测", "Evals", "微调", "Fine-tuning",
    ],
    "RAG & Knowledge Base": [
        "RAG", "知识库", "向量数据库", "Embedding", "Milvus",
        "FAISS", "Qdrant", "Elasticsearch", "BM25", "重排",
        "Rerank", "检索", "召回", "LangChain", "LlamaIndex",
    ],
    "Agentic RL Engineer": [
        "Agentic RL", "强化学习", "Reinforcement Learning", "RL",
        "Reward", "奖励模型", "奖励建模", "Policy", "PPO",
        "DPO", "GRPO", "RLHF", "RLAIF", "Bandit", "Agent",
        "多智能体", "评测", "Evals",
    ],
    "AI Evaluation Engineer": [
        "评测", "Evals", "Benchmark", "数据集", "标注",
        "Reward", "奖励模型", "LLM", "RAG", "Agent",
        "观测", "Tracing", "Telemetry", "LangSmith",
    ],
    "LLMOps / AI Platform": [
        "LLMOps", "MLOps", "模型部署", "模型服务", "LLM",
        "OpenAI", "智谱", "ZhipuAI", "Kubernetes", "Docker",
        "评测", "监控", "Tracing", "Python", "数据管道",
    ],
    "ML Platform / MLOps": [
        "MLOps", "机器学习", "模型部署", "模型服务", "特征工程",
        "数据管道", "Airflow", "Kubeflow", "MLflow", "Docker",
        "Kubernetes", "Python", "PyTorch", "TensorFlow",
    ],
    "Python Backend": [
        "Python", "FastAPI", "Django", "Flask", "SQLAlchemy",
        "PostgreSQL", "MySQL", "Redis", "Celery", "RabbitMQ",
        "异步", "asyncio", "微服务",
    ],
    "Go Backend": [
        "Go", "Golang", "Gin", "gRPC", "微服务", "并发",
        "Goroutine", "Channel", "MySQL", "PostgreSQL", "Redis",
        "Docker", "Kubernetes",
    ],
}

# Placeholder from resume parser when no skills detected
UNKNOWN_SKILL_PLACEHOLDER = "未识别到技能信息"

# Minimum number of matching skills required
MIN_MATCH_COUNT = 1


def check_resume_track_match(
    resume_skills: Optional[List[str]],
    track: str,
) -> Tuple[bool, str]:
    """
    Check if resume skills match the selected job track.

    Args:
        resume_skills: List of skills from resume parsed_json["skills"]
        track: Selected track name (e.g. "Java Backend")

    Returns:
        (match: bool, reason: str)
    """
    if not resume_skills:
        return False, "no_skills"

    # Filter out placeholder / empty
    skills = [
        s.strip() for s in resume_skills
        if s and s.strip() and s.strip() != UNKNOWN_SKILL_PLACEHOLDER
    ]
    if not skills:
        return False, "no_valid_skills"

    keywords = TRACK_SKILL_KEYWORDS.get(track, [])
    if not keywords:
        return True, "ok"  # Unknown track, allow

    # Normalize for comparison (case-insensitive, partial match)
    skills_lower = [s.lower() for s in skills]
    keywords_lower = [k.lower() for k in keywords]

    match_count = 0
    for sk in skills_lower:
        for kw in keywords_lower:
            if kw in sk or sk in kw:
                match_count += 1
                break

    if match_count >= MIN_MATCH_COUNT:
        return True, "ok"
    return False, "mismatch"
