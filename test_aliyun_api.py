#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接测试阿里云API
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
print("阿里云API测试")
print("=" * 60)
print(f"API密钥: {ALIYUN_API_KEY[:10]}...")
print(f"知识库ID: {KNOWLEDGE_BASE_ID}")

# 测试不同的API端点
endpoints = [
    {
        "name": "兼容模式 /chat/completions",
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "payload": {
            "model": "qwen-plus",
            "messages": [
                {
                    "role": "user",
                    "content": "你好"
                }
            ]
        }
    },
    {
        "name": "文本生成 /generation",
        "url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        "payload": {
            "model": "qwen-plus",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": "你好"
                    }
                ]
            }
        }
    },
    {
        "name": "Responses API /responses",
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/responses",
        "payload": {
            "model": "qwen-plus",
            "input": "你好",
            "tools": [
                {
                    "type": "file_search",
                    "vector_store_ids": [KNOWLEDGE_BASE_ID]
                }
            ]
        }
    }
]

headers = {
    "Authorization": f"Bearer {ALIYUN_API_KEY}",
    "Content-Type": "application/json"
}

for endpoint in endpoints:
    print(f"\n{'='*40}")
    print(f"测试端点: {endpoint['name']}")
    print(f"URL: {endpoint['url']}")
    
    try:
        response = requests.post(
            endpoint['url'],
            headers=headers,
            json=endpoint['payload'],
            timeout=10
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 请求成功")
            result = response.json()
            print(f"响应预览: {json.dumps(result, ensure_ascii=False)[:200]}...")
        else:
            print("❌ 请求失败")
            print(f"错误信息: {response.text[:500]}")
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except Exception as e:
        print(f"❌ 请求异常: {e}")

# 测试简单的DashScope API
print(f"\n{'='*40}")
print("测试DashScope简单API")
try:
    # 使用更简单的API
    simple_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    simple_payload = {
        "model": "qwen-turbo",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "你好，请简单回复"
                }
            ]
        },
        "parameters": {
            "result_format": "message"
        }
    }
    
    response = requests.post(simple_url, headers=headers, json=simple_payload, timeout=10)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 简单API请求成功")
        result = response.json()
        if "output" in result and "text" in result["output"]:
            print(f"回复: {result['output']['text']}")
        else:
            print(f"响应: {json.dumps(result, ensure_ascii=False)[:200]}...")
    else:
        print("❌ 简单API请求失败")
        print(f"错误: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ 简单API请求异常: {e}")

print(f"\n{'='*60}")
print("测试完成")
print("=" * 60)