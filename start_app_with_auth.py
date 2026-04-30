#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动带登录认证的AI张老师应用
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def check_dependencies():
    """检查依赖"""
    print("检查Python依赖...")
    
    required_packages = [
        'flask',
        'flask_sqlalchemy',
        'flask_login',
        'werkzeug',
        'bcrypt',
        'python_dotenv',
        'requests',
        'openai',
        'psutil'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        print("正在安装依赖...")
        
        # 安装依赖
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            print("✅ 依赖安装完成!")
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败: {e}")
            return False
    
    return True

def check_database():
    """检查数据库"""
    print("检查数据库...")
    
    db_file = 'app.db'
    if os.path.exists(db_file):
        print(f"✅ 数据库文件存在: {db_file}")
        return True
    else:
        print(f"⚠️  数据库文件不存在，将在启动时自动创建")
        return True

def start_application():
    # """启动应用"""
    # print("\n" + "=" * 50)
    # print("启动AI张老师·数字分身（带登录认证）")
    # print("=" * 50)
    
    # 显示启动信息
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python版本: {sys.version.split()[0]}")
    print(f"工作目录: {os.getcwd()}")
    print(f"数据库: SQLite (app.db)")
    print("\n测试账户:")
    print("  用户名: testuser, 密码: test123")
    print("  用户名: admin, 密码: admin123")
    print("\n访问地址:")
    print("  首页: http://localhost:5004")
    print("  登录: http://localhost:5004/login")
    print("  注册: http://localhost:5004/register")
    print("  应用版: http://localhost:5004/app")
    print("  教育版: http://localhost:5004/pedu")
    print("=" * 50 + "\n")
    
    # 启动应用
    try:
        import app_with_auth
        app_with_auth.app.run(host="0.0.0.0", port=5004, debug=True)
    except KeyboardInterrupt:
        print("\n\n应用已停止")
    except Exception as e:
        print(f"❌ 应用启动失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print("AI张老师·数字分身 - 登录认证系统初始化")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        print("❌ 依赖检查失败")
        return 1
    
    # 检查数据库
    if not check_database():
        print("❌ 数据库检查失败")
        return 1
    
    # 启动应用
    if not start_application():
        print("❌ 应用启动失败")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())