#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
创建用户表、会话表和聊天历史表
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import bcrypt

# 数据库配置
DB_CONFIG = {
    "url": "mysql+pymysql://root:123456@localhost:3306/agent_f",
    "echo": False
}

def create_tables(engine):
    """创建数据库表"""
    
    # 创建用户表
    users_table_sql = """
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
    """
    
    # 创建用户会话表
    user_sessions_table_sql = """
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
    """
    
    # 创建聊天历史表
    chat_history_table_sql = """
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
    
    try:
        with engine.connect() as connection:
            # 创建用户表
            print("创建用户表...")
            connection.execute(text(users_table_sql))
            
            # 创建用户会话表
            print("创建用户会话表...")
            connection.execute(text(user_sessions_table_sql))
            
            # 创建聊天历史表
            print("创建聊天历史表...")
            connection.execute(text(chat_history_table_sql))
            
            connection.commit()
            print("✅ 所有表创建成功!")
            
    except SQLAlchemyError as e:
        print(f"❌ 创建表时出错: {e}")
        return False
    
    return True

def create_test_users(engine):
    """创建测试用户"""
    
    # 测试用户数据
    test_users = [
        {
            "username": "testuser",
            "password": "test123",
            "email": "test@example.com",
            "full_name": "测试用户"
        },
        {
            "username": "admin",
            "password": "admin123",
            "email": "admin@example.com",
            "full_name": "管理员"
        }
    ]
    
    try:
        with engine.connect() as connection:
            for user_data in test_users:
                # 检查用户是否已存在
                check_sql = text("SELECT id FROM users WHERE username = :username")
                result = connection.execute(check_sql, {"username": user_data["username"]}).fetchone()
                
                if result:
                    print(f"用户 '{user_data['username']}' 已存在，跳过...")
                    continue
                
                # 加密密码
                password_hash = bcrypt.hashpw(
                    user_data["password"].encode('utf-8'),
                    bcrypt.gensalt()
                ).decode('utf-8')
                
                # 插入用户
                insert_sql = text("""
                    INSERT INTO users (username, password_hash, email, full_name)
                    VALUES (:username, :password_hash, :email, :full_name)
                """)
                
                connection.execute(insert_sql, {
                    "username": user_data["username"],
                    "password_hash": password_hash,
                    "email": user_data["email"],
                    "full_name": user_data["full_name"]
                })
                
                print(f"✅ 创建用户: {user_data['username']} (密码: {user_data['password']})")
            
            connection.commit()
            print("✅ 测试用户创建完成!")
            
    except SQLAlchemyError as e:
        print(f"❌ 创建测试用户时出错: {e}")
        return False
    
    return True

def main():
    """主函数"""
    
    print("=" * 50)
    print("数据库初始化脚本")
    print("=" * 50)
    
    try:
        # 创建数据库引擎
        engine = create_engine(
            DB_CONFIG["url"],
            echo=DB_CONFIG["echo"],
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        # 测试连接
        print("测试数据库连接...")
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print(f"✅ 数据库连接成功!")
        
        # 创建表
        if not create_tables(engine):
            print("❌ 表创建失败")
            return 1
        
        # 创建测试用户
        create_test_users_option = input("\n是否创建测试用户? (y/n): ").strip().lower()
        if create_test_users_option == 'y':
            if not create_test_users(engine):
                print("❌ 测试用户创建失败")
                return 1
        
        print("\n" + "=" * 50)
        print("数据库初始化完成!")
        print("=" * 50)
        
        # 显示表信息
        print("\n数据库表信息:")
        with engine.connect() as connection:
            tables = connection.execute(text("SHOW TABLES")).fetchall()
            for table in tables:
                print(f"  - {table[0]}")
        
        return 0
        
    except SQLAlchemyError as e:
        print(f"❌ 数据库连接失败: {e}")
        print("\n请检查:")
        print("1. MySQL服务是否运行")
        print("2. 数据库连接配置是否正确")
        print("3. 数据库 'agent_f' 是否存在")
        return 1
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("\n请安装依赖:")
        print("pip install pymysql sqlalchemy bcrypt")
        return 1

if __name__ == "__main__":
    sys.exit(main())