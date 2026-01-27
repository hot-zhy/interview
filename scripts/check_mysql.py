"""Check MySQL service status and connection."""
import sys
import os
import subprocess
import platform

def check_mysql_service():
    """Check if MySQL service is running."""
    print("=" * 50)
    print("检查 MySQL 服务状态")
    print("=" * 50)
    print()
    
    system = platform.system()
    
    if system == "Windows":
        print("检测到 Windows 系统")
        print()
        
        # Check service status
        try:
            result = subprocess.run(
                ["sc", "query", "MySQL80"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if "RUNNING" in result.stdout:
                print("✅ MySQL 服务正在运行")
                return True
            elif "STOPPED" in result.stdout:
                print("❌ MySQL 服务已停止")
                print()
                print("启动 MySQL 服务的方法：")
                print("1. 以管理员身份打开 PowerShell 或 CMD")
                print("2. 执行以下命令：")
                print("   net start MySQL80")
                print()
                print("或者使用服务管理器：")
                print("1. 按 Win+R，输入 services.msc")
                print("2. 找到 MySQL80 服务")
                print("3. 右键点击 -> 启动")
                return False
            else:
                # Try other common MySQL service names
                for service_name in ["MySQL", "MySQL57", "MySQL80", "MYSQL"]:
                    result = subprocess.run(
                        ["sc", "query", service_name],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if "RUNNING" in result.stdout:
                        print(f"✅ MySQL 服务 ({service_name}) 正在运行")
                        return True
                
                print("⚠️  无法检测到 MySQL 服务")
                print("可能的原因：")
                print("1. MySQL 未安装")
                print("2. 服务名称不是 MySQL80")
                print()
                print("请手动检查：")
                print("1. 打开服务管理器 (services.msc)")
                print("2. 查找名称包含 'MySQL' 的服务")
                return False
                
        except FileNotFoundError:
            print("⚠️  无法执行服务检查命令")
            print("请手动检查 MySQL 服务状态")
            return False
        except Exception as e:
            print(f"检查服务时出错: {e}")
            return False
    
    elif system == "Linux":
        print("检测到 Linux 系统")
        print()
        
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "mysql"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                print("✅ MySQL 服务正在运行")
                return True
            else:
                print("❌ MySQL 服务未运行")
                print()
                print("启动 MySQL 服务：")
                print("sudo systemctl start mysql")
                print("或")
                print("sudo service mysql start")
                return False
                
        except FileNotFoundError:
            print("⚠️  无法执行 systemctl 命令")
            return False
        except Exception as e:
            print(f"检查服务时出错: {e}")
            return False
    
    elif system == "Darwin":  # macOS
        print("检测到 macOS 系统")
        print()
        
        try:
            result = subprocess.run(
                ["brew", "services", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if "mysql" in result.stdout.lower() and "started" in result.stdout.lower():
                print("✅ MySQL 服务正在运行")
                return True
            else:
                print("❌ MySQL 服务未运行")
                print()
                print("启动 MySQL 服务：")
                print("brew services start mysql")
                return False
                
        except FileNotFoundError:
            print("⚠️  请手动检查 MySQL 服务状态")
            return False
        except Exception as e:
            print(f"检查服务时出错: {e}")
            return False
    
    else:
        print(f"⚠️  未识别的操作系统: {system}")
        print("请手动检查 MySQL 服务状态")
        return False


def test_mysql_connection():
    """Test MySQL connection."""
    print()
    print("=" * 50)
    print("测试 MySQL 连接")
    print("=" * 50)
    print()
    
    try:
        import pymysql
        
        # Try to connect without database
        print("尝试连接到 MySQL 服务器...")
        print("提示：如果连接失败，请检查 .env 文件中的数据库配置")
        print()
        
        from backend.core.config import settings
        
        db_url = settings.database_url
        if "mysql" not in db_url:
            print(f"当前配置不是 MySQL: {db_url}")
            return False
        
        from urllib.parse import urlparse
        parsed = urlparse(db_url.replace("mysql+pymysql://", "mysql://"))
        user = parsed.username or "root"
        password = parsed.password or ""
        host = parsed.hostname or "localhost"
        port = parsed.port or 3306
        
        print(f"连接信息：")
        print(f"  主机: {host}:{port}")
        print(f"  用户: {user}")
        print(f"  密码: {'已设置' if password else '未设置'}")
        print()
        
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4'
        )
        
        print("✅ MySQL 连接成功！")
        connection.close()
        return True
        
    except ImportError:
        print("❌ 未安装 pymysql")
        print("请运行: pip install pymysql")
        return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print()
        print("可能的原因：")
        print("1. MySQL 服务未启动")
        print("2. 用户名或密码错误")
        print("3. 主机或端口配置错误")
        print("4. 防火墙阻止连接")
        print()
        print("请检查 .env 文件中的 DATABASE_URL 配置")
        return False


def main():
    """Main function."""
    service_running = check_mysql_service()
    
    if service_running:
        test_mysql_connection()
    else:
        print()
        print("=" * 50)
        print("下一步操作")
        print("=" * 50)
        print()
        print("1. 先启动 MySQL 服务（见上方说明）")
        print("2. 然后重新运行此脚本检查连接")
        print("3. 或手动创建数据库（见下方）")
        print()
        print("手动创建数据库的方法：")
        print("1. 打开命令行/终端")
        print("2. 登录 MySQL:")
        print("   mysql -u root -p")
        print("3. 执行 SQL:")
        print("   CREATE DATABASE interview_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        print("   EXIT;")


if __name__ == "__main__":
    main()

