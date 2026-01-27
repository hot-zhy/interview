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
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

