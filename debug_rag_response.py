#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试RAG响应解析
"""

import os
import requests
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取配置
ALIYUN_API_KEY = os.getenv("ALIYUN_API_KEY")
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID")

print("=" * 60)
print("调试RAG响应解析")
print("=" * 60)

# 使用Responses API进行测试
url = "https://dashscope.aliyuncs.com/compatible-mode/v1/responses"
headers = {
    "Authorization": f"Bearer {ALIYUN_API_KEY}",
    "Content-Type": "application/json"
}

# 测试问题
test_questions = [
    "计算机专业就业前景怎么样？",
    "什么是人工智能？"
]

for question in test_questions:
    print(f"\n{'='*40}")
    print(f"测试问题: {question}")
    
    payload = {
        "model": "qwen-plus",
        "input": question,
        "tools": [
            {
                "type": "file_search",
                "vector_store_ids": [KNOWLEDGE_BASE_ID]
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n完整响应结构:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # 尝试不同的解析方式
            print(f"\n尝试解析响应文本:")
            
            # 方式1: 直接获取output.text
            if "output" in result and isinstance(result["output"], list):
                print("方式1: output是列表")
                for i, item in enumerate(result["output"]):
                    print(f"  output[{i}]: {item}")
                    if "content" in item:
                        for j, content in enumerate(item["content"]):
                            print(f"    content[{j}]: {content}")
                            if content.get("type") == "output_text":
                                print(f"      找到output_text: {content.get('text', '')[:100]}...")
            
            # 方式2: 检查是否有text字段
            if "output" in result and "text" in result["output"]:
                print(f"方式2: output.text = {result['output']['text'][:100]}...")
            
            # 方式3: 检查choices
            if "choices" in result:
                print(f"方式3: choices found, count = {len(result['choices'])}")
                for i, choice in enumerate(result["choices"]):
                    if "message" in choice and "content" in choice["message"]:
                        print(f"  choice[{i}].message.content = {choice['message']['content'][:100]}...")
            
            # 方式4: 递归搜索所有文本
            def find_text(obj, path=""):
                texts = []
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_path = f"{path}.{key}" if path else key
                        if key == "text" and isinstance(value, str):
                            texts.append((new_path, value))
                        elif isinstance(value, (dict, list)):
                            texts.extend(find_text(value, new_path))
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        new_path = f"{path}[{i}]"
                        texts.extend(find_text(item, new_path))
                return texts
            
            all_texts = find_text(result)
            if all_texts:
                print(f"\n方式4: 找到 {len(all_texts)} 个文本字段:")
                for path, text in all_texts[:5]:  # 只显示前5个
                    print(f"  {path}: {text[:100]}...")
            
        else:
            print(f"请求失败: {response.text[:500]}")
            
    except Exception as e:
        print(f"请求异常: {e}")

print(f"\n{'='*60}")
print("调试完成")
print("=" * 60)