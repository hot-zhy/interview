# 数据库设置指南

## MySQL 配置

系统已配置为使用 MySQL 数据库。请按照以下步骤设置：

### 1. 安装 MySQL

确保已安装 MySQL 服务器（推荐 MySQL 8.0+）。

### 2. 创建数据库

登录 MySQL 并创建数据库：

```sql
CREATE DATABASE interview_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

或者使用命令行：

```bash
mysql -u root -p -e "CREATE DATABASE interview_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 3. 配置环境变量

在 `.env` 文件中配置数据库连接：

```env
DATABASE_URL=mysql+pymysql://用户名:密码@主机:端口/数据库名?charset=utf8mb4
```

示例：

```env
# 本地 MySQL
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/interview_db?charset=utf8mb4

# 远程 MySQL
DATABASE_URL=mysql+pymysql://user:pass@192.168.1.100:3306/interview_db?charset=utf8mb4
```

### 4. 安装依赖

确保已安装 MySQL 驱动：

```bash
pip install pymysql cryptography
```

或重新安装所有依赖：

```bash
pip install -r requirements.txt
```

### 5. 初始化数据库

**方式一：使用初始化脚本（推荐）**

```bash
python scripts/init_db.py
```

此脚本会自动创建数据库（如果不存在）和所有表。

**方式二：使用 Alembic 迁移**

```bash
alembic upgrade head
```

### 6. 验证

运行应用并尝试注册一个用户，如果成功则说明数据库配置正确。

## 故障排除

### 连接错误

如果遇到连接错误，检查：

1. MySQL 服务是否运行
2. 用户名和密码是否正确
3. 数据库是否存在
4. 防火墙是否允许连接

### 字符编码问题

确保数据库使用 `utf8mb4` 字符集：

```sql
ALTER DATABASE interview_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 权限问题

确保 MySQL 用户有创建数据库和表的权限：

```sql
GRANT ALL PRIVILEGES ON interview_db.* TO 'your_user'@'localhost';
FLUSH PRIVILEGES;
```

## 回退到 SQLite（可选）

如果不想使用 MySQL，可以在 `.env` 中配置 SQLite：

```env
DATABASE_URL=sqlite:///./data/interview.db
```

然后运行初始化脚本即可。

