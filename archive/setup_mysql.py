#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置MySQL数据库和用户
"""

import subprocess
import time
import os
import sys

def run_command(cmd, check=True):
    """运行命令并返回结果"""
    print(f"执行: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if check and result.returncode != 0:
            print(f"错误: {result.stderr}")
        return result
    except Exception as e:
        print(f"执行命令时出错: {e}")
        return None

def stop_mysql():
    """停止MySQL服务"""
    print("\n停止MySQL服务...")
    result = run_command("brew services stop mysql", check=False)
    time.sleep(3)
    return result

def start_mysql_safe():
    """以安全模式启动MySQL"""
    print("\n以安全模式启动MySQL...")
    
    # 检查是否已有mysqld进程
    run_command("pkill mysqld", check=False)
    time.sleep(2)
    
    # 启动安全模式
    cmd = "mysqld_safe --skip-grant-tables &"
    result = run_command(cmd, check=False)
    time.sleep(5)
    return result

def reset_root_password():
    """重置root密码"""
    print("\n重置root密码...")
    
    # 尝试多种方法
    methods = [
        # 方法1: 直接设置空密码
        "mysql -u root -e \"ALTER USER 'root'@'localhost' IDENTIFIED BY '';\"",
        # 方法2: 使用mysql_native_password
        "mysql -u root -e \"ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '';\"",
        # 方法3: 更新mysql.user表
        "mysql -u root -e \"USE mysql; UPDATE user SET authentication_string='' WHERE User='root'; FLUSH PRIVILEGES;\"",
    ]
    
    for method in methods:
        result = run_command(method, check=False)
        if result and result.returncode == 0:
            print(f"✅ 密码重置成功!")
            return True
    
    print("❌ 所有密码重置方法都失败了")
    return False

def start_mysql_normal():
    """正常启动MySQL"""
    print("\n正常启动MySQL...")
    result = run_command("brew services start mysql", check=False)
    time.sleep(5)
    return result

def create_database():
    """创建数据库和表"""
    print("\n创建数据库和表...")
    
    # 创建数据库
    create_db_cmd = "mysql -u root -e \"CREATE DATABASE IF NOT EXISTS agent_f CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\""
    result = run_command(create_db_cmd)
    if not result or result.returncode != 0:
        print("❌ 创建数据库失败")
        return False
    
    # 创建表的SQL
    sql_commands = [
        "USE agent_f;",
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            email VARCHAR(100) UNIQUE,
            full_name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL,
            is_active BOOLEAN DEFAULT TRUE,
            INDEX idx_username (username),
            INDEX idx_email (email)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            session_id VARCHAR(100) UNIQUE NOT NULL,
            ip_address VARCHAR(45),
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NULL,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_session_id (session_id),
            INDEX idx_user_id (user_id),
            INDEX idx_expires_at (expires_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            session_id VARCHAR(100) NOT NULL,
            message_type ENUM('user', 'assistant', 'system') NOT NULL,
            content TEXT NOT NULL,
            context TEXT,
            response_time FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_user_id (user_id),
            INDEX idx_session_id (session_id),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    ]
    
    # 执行所有SQL命令
    for sql in sql_commands:
        cmd = f'mysql -u root -e "{sql}"'
        result = run_command(cmd, check=False)
        if result and result.returncode != 0:
            print(f"❌ 执行SQL失败: {sql[:50]}...")
            return False
    
    print("✅ 数据库和表创建成功!")
    return True

def test_connection():
    """测试数据库连接"""
    print("\n测试数据库连接...")
    
    # 测试MySQL连接
    test_cmd = "mysql -u root -e \"SELECT VERSION(); SHOW DATABASES LIKE 'agent_f';\""
    result = run_command(test_cmd)
    
    if result and result.returncode == 0:
        print("✅ MySQL连接测试成功!")
        print(f"输出:\n{result.stdout}")
        return True
    else:
        print("❌ MySQL连接测试失败")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("MySQL数据库设置工具")
    print("=" * 50)
    
    # 检查MySQL是否安装
    print("检查MySQL安装...")
    result = run_command("which mysql", check=False)
    if not result or result.returncode != 0:
        print("❌ MySQL未安装，请先安装MySQL")
        print("运行: brew install mysql")
        return 1
    
    # 停止MySQL
    stop_mysql()
    
    # 以安全模式启动
    start_mysql_safe()
    
    # 重置密码
    if not reset_root_password():
        print("⚠️  密码重置可能失败，继续尝试...")
    
    # 停止安全模式
    print("\n停止安全模式...")
    run_command("pkill mysqld", check=False)
    time.sleep(3)
    
    # 正常启动
    start_mysql_normal()
    
    # 创建数据库
    if not create_database():
        print("❌ 数据库创建失败")
        return 1
    
    # 测试连接
    if not test_connection():
        print("❌ 连接测试失败")
        return 1
    
    print("\n" + "=" * 50)
    print("✅ 数据库设置完成!")
    print("=" * 50)
    print("\n数据库信息:")
    print("数据库名: agent_f")
    print("用户名: root")
    print("密码: (空)")
    print("连接URL: mysql+pymysql://root:@localhost:3306/agent_f")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())