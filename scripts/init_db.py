"""Initialize database."""
import sys
import os
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from backend.db.base import Base, engine
from backend.core.config import settings

# Import all models to ensure they are registered with Base.metadata
from backend.db.models import (  # noqa
    User, Resume, QuestionBank, InterviewSession,
    InterviewTurn, AskedQuestion, Evaluation, Report
)

def init_db():
    """Initialize database and tables."""
    print("=" * 50)
    print("初始化数据库")
    print("=" * 50)
    print(f"数据库连接: {settings.database_url}")
    print()
    
    # For MySQL, create database if it doesn't exist
    if "mysql" in settings.database_url:
        parsed = urlparse(settings.database_url.replace("mysql+pymysql://", "mysql://"))
        db_name = parsed.path.lstrip("/").split("?")[0]
        
        # Create connection without database name
        base_url = settings.database_url.rsplit("/", 1)[0]
        admin_engine = create_engine(base_url + "/mysql", pool_pre_ping=True)
        
        try:
            with admin_engine.connect() as conn:
                # Create database if not exists
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                conn.commit()
            print(f"✅ 数据库 '{db_name}' 已创建或已存在")
        except Exception as e:
            print(f"⚠️  无法创建数据库（可能已存在）: {e}")
        finally:
            admin_engine.dispose()
    
    # Create tables
    print()
    print("正在创建数据表...")
    try:
        Base.metadata.create_all(bind=engine)
        
        # Verify tables were created
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print()
        print("✅ 数据表创建完成！")
        print(f"已创建的表 ({len(tables)} 个):")
        for table in sorted(tables):
            print(f"  - {table}")
        
        print()
        print(f"数据库初始化完成: {settings.database_url}")
        
    except Exception as e:
        print(f"❌ 创建数据表时出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    init_db()

