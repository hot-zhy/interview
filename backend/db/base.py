"""Database base configuration."""
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.core.config import settings


def _resolve_sqlite_url(url: str) -> str:
    """Resolve relative SQLite URLs to a stable project path."""
    if not url.startswith("sqlite:///"):
        return url

    sqlite_path = url.replace("sqlite:///", "", 1).strip()
    if not sqlite_path:
        sqlite_path = "data/interview.db"

    candidate = Path(sqlite_path)
    if not candidate.is_absolute():
        # Keep SQLite db under interview/data regardless of launch cwd.
        project_root = Path(__file__).resolve().parents[2]
        candidate = project_root / candidate

    candidate.parent.mkdir(parents=True, exist_ok=True)
    # SQLAlchemy expects sqlite:/// + POSIX-style absolute path.
    return f"sqlite:///{candidate.as_posix()}"

# Configure engine based on database type
database_url = settings.database_url
connect_args = {}
if "sqlite" in settings.database_url:
    database_url = _resolve_sqlite_url(settings.database_url)
    connect_args = {"check_same_thread": False}
elif "mysql" in settings.database_url:
    # MySQL connection arguments
    connect_args = {
        "charset": "utf8mb4",
        "connect_timeout": 10
    }

engine = create_engine(
    database_url,
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

