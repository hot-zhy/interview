"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = "mysql+pymysql://root:password@localhost:3306/interview_db?charset=utf8mb4"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    
    # LLM (Optional)
    zhipuai_api_key: Optional[str] = None
    zhipuai_model: str = "glm-4-flash"
    
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

    selector_strategy: str = "weighted_random"  # "weighted_random" | "thompson_sampling"
    thompson_alpha0: float = 1.0
    thompson_beta0: float = 1.0
    success_threshold: float = 0.70  # success if overall_score >= threshold
    recent_chapter_avoid_k: int = 2  # avoid last k chapters when possible
    thompson_context: str = "chapter_difficulty"  # "chapter" | "chapter_difficulty"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

