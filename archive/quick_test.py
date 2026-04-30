#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速测试应用ID调用接口
"""

import requests
import json
import time

def quick_test():
    """快速测试"""
    base_url = "http://localhost:5002"
    
    print("快速测试应用ID调用接口")
    print("=" * 50)
    
    # 1. 测试健康检查
    print("\n1. 测试健康检查...")
    try:
        resp = requests.get(f"{base_url}/health", timeout=5)
        print(f"   状态: {resp.status_code}")
        print(f"   响应: {resp.json()}")
    except Exception as e:
        print(f"   失败: {e}")
        return
    
    # 2. 测试应用测试接口
    print("\n2. 测试应用配置...")
    try:
        resp = requests.get(f"{base_url}/app/test", timeout=10)
        data = resp.json()
        print(f"   状态: {resp.status_code}")
        print(f"   应用ID配置: {data.get('app_id_configured')}")
        print(f"   API密钥配置: {data.get('api_key_configured')}")
        print(f"   测试成功: {data.get('success')}")
        
        if data.get('success'):
            print(f"   响应: {data.get('output', '')[:80]}...")
        else:
            print(f"   错误: {data.get('error', '')}")
    except Exception as e:
        print(f"   失败: {e}")
        return
    
    # 3. 测试聊天接口
    print("\n3. 测试聊天接口...")
    try:
        payload = {
            "question": "你好，请介绍一下你自己",
            "use_cache": True
        }
        
        start = time.time()
        resp = requests.post(f"{base_url}/app/chat", 
                           json=payload,
                           headers={"Content-Type": "application/json"},
                           timeout=15)
        duration = time.time() - start
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"   状态: {resp.status_code}")
            print(f"   总耗时: {duration:.2f}秒")
            print(f"   处理时间: {data.get('processing_time', 0):.2f}秒")
            print(f"   缓存命中: {data.get('cached', False)}")
            print(f"   成功: {data.get('success', False)}")
            
            if data.get('success'):
                answer = data.get('answer', '')
                print(f"   回答长度: {len(answer)} 字符")
                print(f"   回答预览: {answer[:100]}...")
            else:
                print(f"   错误: {data.get('error', '')}")
        else:
            print(f"   失败，状态码: {resp.status_code}")
            print(f"   响应: {resp.text[:200]}")
            
    except requests.exceptions.Timeout:
        print("   请求超时（15秒）")
    except Exception as e:
        print(f"   失败: {e}")
    
    print("\n" + "=" * 50)
    print("测试完成")

if __name__ == "__main__":
    quick_test()