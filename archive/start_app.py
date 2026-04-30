#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
启动脚本 - 支持自定义端口
"""

import sys
import os
import argparse

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='启动AI张老师服务')
    parser.add_argument('--port', type=int, default=5001, help='服务端口 (默认: 5001)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='绑定地址 (默认: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    print(f"启动AI张老师服务...")
    print(f"地址: {args.host}")
    print(f"端口: {args.port}")
    print(f"调试模式: {args.debug}")
    print(f"Redis缓存: 已启用")
    print("-" * 50)
    
    # 启动应用
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        threaded=True
    )

if __name__ == "__main__":
    main()