"""Create MySQL database if it doesn't exist."""
import sys
import os
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from backend.core.config import settings

def create_database():
    """Create MySQL database if it doesn't exist."""
    print("=" * 50)
    print("创建 MySQL 数据库")
    print("=" * 50)
    
    # Parse database URL
    db_url = settings.database_url
    
    if "mysql" not in db_url:
        print(f"错误：当前配置不是 MySQL 数据库")
        print(f"当前配置: {db_url}")
        return False
    
    # Extract database name and connection info
    parsed = urlparse(db_url.replace("mysql+pymysql://", "mysql://"))
    db_name = parsed.path.lstrip("/").split("?")[0]
    user = parsed.username or "root"
    password = parsed.password or ""
    host = parsed.hostname or "localhost"
    port = parsed.port or 3306
    
    print(f"数据库名称: {db_name}")
    print(f"主机: {host}:{port}")
    print(f"用户: {user}")
    print()
    
    # Create connection URL without database name
    if password:
        base_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/mysql"
    else:
        base_url = f"mysql+pymysql://{user}@{host}:{port}/mysql"
    
    try:
        print("正在连接 MySQL 服务器...")
        admin_engine = create_engine(base_url, pool_pre_ping=True)
        
        with admin_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(text(f"SHOW DATABASES LIKE '{db_name}'"))
            exists = result.fetchone() is not None
            
            if exists:
                print(f"数据库 '{db_name}' 已存在")
                response = input("是否要删除并重新创建？(y/N): ").strip().lower()
                if response == 'y':
                    conn.execute(text(f"DROP DATABASE `{db_name}`"))
                    print(f"已删除数据库 '{db_name}'")
                else:
                    print("跳过创建")
                    return True
            
            # Create database
            print(f"正在创建数据库 '{db_name}'...")
            conn.execute(text(
                f"CREATE DATABASE `{db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
            conn.commit()
            print(f"✅ 数据库 '{db_name}' 创建成功！")
            return True
            
    except Exception as e:
        print(f"❌ 创建数据库失败: {e}")
        print()
        print("请检查：")
        print("1. MySQL 服务是否正在运行")
        print("2. 用户名和密码是否正确")
        print("3. 用户是否有创建数据库的权限")
        print()
        print("你也可以手动执行以下 SQL 语句：")
        print(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        return False
    finally:
        if 'admin_engine' in locals():
            admin_engine.dispose()

if __name__ == "__main__":
    success = create_database()
    if success:
        print()
        print("下一步：运行 python scripts/init_db.py 来创建数据表")
    sys.exit(0 if success else 1)
