#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接测试RAG服务，不经过Flask应用
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_service_improved import rag_service
import time

def test_rag_directly():
    """直接测试RAG服务"""
    print("=" * 60)
    print("直接测试RAG服务")
    print("=" * 60)
    
    # 测试连接
    print("\n1. 测试API连接...")
    if rag_service.test_connection():
        print("✅ API连接成功")
    else:
        print("❌ API连接失败")
        return
    
    # 测试搜索
    test_questions = [
        "计算机专业就业前景怎么样？",
        "如何准备考研？",
        "什么是人工智能？",
        "普通家庭学什么专业好？"
    ]
    
    print("\n2. 测试知识库搜索...")
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. 问题: {question}")
        start_time = time.time()
        
        try:
            result = rag_service.search_knowledge(question)
            duration = time.time() - start_time
            
            if result:
                print(f"   ✅ 搜索成功 (耗时: {duration:.2f}s)")
                print(f"   结果长度: {len(result)} 字符")
                print(f"   结果预览: {result[:200]}...")
            else:
                print(f"   ❌ 搜索失败 (耗时: {duration:.2f}s)")
                print(f"   原因: 返回空结果")
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"   ❌ 搜索异常 (耗时: {duration:.2f}s)")
            print(f"   异常: {e}")
    
    # 测试备用方案
    print("\n3. 测试备用方案...")
    test_question = "测试一个没有相关上下文的问题"
    start_time = time.time()
    result = rag_service.search_knowledge(test_question)
    duration = time.time() - start_time
    
    if result:
        print(f"   ✅ 备用方案生效 (耗时: {duration:.2f}s)")
        print(f"   结果: {result}")
    else:
        print(f"   ❌ 备用方案未生效 (耗时: {duration:.2f}s)")

if __name__ == "__main__":
    test_rag_directly()