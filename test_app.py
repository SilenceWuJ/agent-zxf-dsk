#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json

def test_flask_app():
    """测试Flask应用是否正常工作"""
    
    # 测试主页
    print("测试主页访问...")
    try:
        response = requests.get("http://localhost:5000/", timeout=5)
        if response.status_code == 200:
            print("✅ 主页访问成功")
            # 检查是否包含关键元素
            if "AI张老师" in response.text:
                print("✅ 页面内容正确")
            else:
                print("⚠️  页面内容可能有问题")
        else:
            print(f"❌ 主页访问失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 主页访问异常: {e}")
    
    print("\n测试API接口...")
    # 测试聊天API
    test_data = {
        "question": "计算机专业前景怎么样？"
    }
    
    try:
        response = requests.post(
            "http://localhost:5000/chat",
            json=test_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API接口访问成功")
            print(f"   问题: {test_data['question']}")
            print(f"   回答长度: {len(result.get('answer', ''))} 字符")
            if result.get('answer'):
                print("✅ 成功获取回答")
            else:
                print("⚠️  回答为空")
        else:
            print(f"❌ API接口失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"❌ API接口异常: {e}")

if __name__ == "__main__":
    print("开始测试AI张老师数字分身Flask应用...")
    print("=" * 50)
    test_flask_app()
    print("=" * 50)
    print("测试完成")