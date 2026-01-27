"""Database base configuration."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.core.config import settings
import os

# Create data directory if it doesn't exist (for SQLite fallback)
os.makedirs("data", exist_ok=True)

# Configure engine based on database type
connect_args = {}
if "sqlite" in settings.database_url:
    connect_args = {"check_same_thread": False}
elif "mysql" in settings.database_url:
    # MySQL connection arguments
    connect_args = {
        "charset": "utf8mb4",
        "connect_timeout": 10
    }

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.debug,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

