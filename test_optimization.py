#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
优化效果测试脚本
对比原始版本和优化版本的性能差异
"""

import time
import requests
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

# 测试配置
BASE_URL = "http://localhost:5000"
TEST_QUESTIONS = [
    "计算机专业就业前景怎么样？",
    "普通家庭学什么专业好？",
    "985和211大学有什么区别？",
    "考研应该怎么准备？",
    "人工智能专业值得学吗？",
    "医学专业的学习难度大吗？",
    "金融专业的就业方向有哪些？",
    "如何选择适合自己的大学？",
    "考研复试需要注意什么？",
    "软件工程和计算机科学有什么区别？"
]

def test_original_chat(question, need_audio=False):
    """测试原始版本"""
    url = f"{BASE_URL}/chat"
    payload = {
        "question": question,
        "need_audio": need_audio
    }
    
    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=30)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "time": response_time,
                "answer_length": len(data.get("answer", "")),
                "has_audio": "audio_base64" in data
            }
        else:
            return {
                "success": False,
                "time": response_time,
                "error": f"HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            "success": False,
            "time": time.time() - start_time,
            "error": str(e)
        }

def test_optimized_chat(question, need_audio=False):
    """测试优化版本"""
    url = f"{BASE_URL}/chat"
    payload = {
        "question": question,
        "need_audio": need_audio
    }
    
    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=30)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "time": response_time,
                "answer_length": len(data.get("answer", "")),
                "has_audio": "audio_base64" in data,
                "processing_time": data.get("processing_time", 0),
                "cached": data.get("cached", False)
            }
        else:
            return {
                "success": False,
                "time": response_time,
                "error": f"HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            "success": False,
            "time": time.time() - start_time,
            "error": str(e)
        }

def run_performance_test(test_func, test_name, questions, need_audio=False, workers=3):
    """运行性能测试"""
    print(f"\n{'='*60}")
    print(f"开始 {test_name} 性能测试")
    print(f"测试问题数量: {len(questions)}")
    print(f"音频合成: {'开启' if need_audio else '关闭'}")
    print(f"并发数: {workers}")
    print(f"{'='*60}")
    
    results = []
    success_count = 0
    total_time = 0
    
    # 使用线程池并发测试
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(test_func, q, need_audio): q for q in questions}
        
        for future in as_completed(futures):
            question = futures[future]
            try:
                result = future.result(timeout=35)
                results.append(result)
                
                if result["success"]:
                    success_count += 1
                    total_time += result["time"]
                    status = "✓"
                else:
                    status = "✗"
                
                print(f"{status} 问题: {question[:30]}...")
                print(f"   时间: {result['time']:.2f}s, 成功: {result['success']}")
                if result.get("cached") is not None:
                    print(f"   缓存: {result['cached']}")
                
            except Exception as e:
                print(f"✗ 问题: {question[:30]}... 测试异常: {e}")
    
    # 分析结果
    if success_count > 0:
        success_times = [r["time"] for r in results if r["success"]]
        
        print(f"\n{'='*60}")
        print(f"{test_name} 测试结果:")
        print(f"总请求数: {len(questions)}")
        print(f"成功数: {success_count}")
        print(f"成功率: {success_count/len(questions)*100:.1f}%")
        print(f"总耗时: {total_time:.2f}s")
        print(f"平均响应时间: {statistics.mean(success_times):.2f}s")
        print(f"最小响应时间: {min(success_times):.2f}s")
        print(f"最大响应时间: {max(success_times):.2f}s")
        print(f"中位数响应时间: {statistics.median(success_times):.2f}s")
        
        if len(success_times) >= 2:
            print(f"标准差: {statistics.stdev(success_times):.2f}s")
        
        # 计算百分位数
        if len(success_times) >= 10:
            p95 = statistics.quantiles(success_times, n=20)[18]
            print(f"P95响应时间: {p95:.2f}s")
        
        return {
            "test_name": test_name,
            "total_requests": len(questions),
            "success_count": success_count,
            "success_rate": success_count/len(questions)*100,
            "avg_time": statistics.mean(success_times),
            "min_time": min(success_times),
            "max_time": max(success_times),
            "median_time": statistics.median(success_times)
        }
    else:
        print(f"\n{test_name} 测试失败: 所有请求都失败了")
        return None

def test_cache_effectiveness():
    """测试缓存效果"""
    print(f"\n{'='*60}")
    print("测试缓存效果")
    print(f"{'='*60}")
    
    # 第一次请求（应该未命中缓存）
    print("第一次请求（应该未命中缓存）:")
    result1 = test_optimized_chat(TEST_QUESTIONS[0], need_audio=False)
    print(f"时间: {result1['time']:.2f}s, 缓存: {result1.get('cached', 'N/A')}")
    
    # 第二次请求（应该命中缓存）
    print("\n第二次请求（应该命中缓存）:")
    result2 = test_optimized_chat(TEST_QUESTIONS[0], need_audio=False)
    print(f"时间: {result2['time']:.2f}s, 缓存: {result2.get('cached', 'N/A')}")
    
    # 计算缓存加速比
    if result1["success"] and result2["success"]:
        speedup = result1["time"] / result2["time"] if result2["time"] > 0 else 0
        print(f"\n缓存加速比: {speedup:.2f}x")
        print(f"时间减少: {result1['time'] - result2['time']:.2f}s")
        print(f"性能提升: {(1 - result2['time']/result1['time'])*100:.1f}%")

def test_concurrent_requests():
    """测试并发请求"""
    print(f"\n{'='*60}")
    print("测试并发请求性能")
    print(f"{'='*60}")
    
    # 使用相同问题测试并发
    same_question = TEST_QUESTIONS[0]
    concurrent_count = 5
    
    print(f"并发请求数: {concurrent_count}")
    print(f"测试问题: {same_question}")
    
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
        futures = [executor.submit(test_optimized_chat, same_question, False) 
                  for _ in range(concurrent_count)]
        
        results = []
        for future in as_completed(futures):
            try:
                results.append(future.result(timeout=30))
            except Exception as e:
                print(f"并发请求失败: {e}")
    
    total_time = time.time() - start_time
    success_results = [r for r in results if r["success"]]
    
    if success_results:
        times = [r["time"] for r in success_results]
        print(f"\n并发测试结果:")
        print(f"总时间: {total_time:.2f}s")
        print(f"成功数: {len(success_results)}/{concurrent_count}")
        print(f"平均响应时间: {statistics.mean(times):.2f}s")
        print(f"吞吐量: {len(success_results)/total_time:.2f} 请求/秒")

def main():
    """主测试函数"""
    print("AI张老师性能优化测试")
    print(f"测试服务器: {BASE_URL}")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查服务是否可用
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            print(f"服务状态: 正常")
        else:
            print(f"服务状态: 异常 (HTTP {health_response.status_code})")
            return
    except Exception as e:
        print(f"服务不可用: {e}")
        return
    
    # 运行性能测试
    all_results = []
    
    # 测试1: 无音频优化版本
    result1 = run_performance_test(
        test_optimized_chat, 
        "优化版本（无音频）", 
        TEST_QUESTIONS, 
        need_audio=False,
        workers=3
    )
    if result1:
        all_results.append(result1)
    
    # 测试2: 有音频优化版本
    result2 = run_performance_test(
        test_optimized_chat, 
        "优化版本（有音频）", 
        TEST_QUESTIONS[:5],  # 减少测试数量，因为TTS比较耗时
        need_audio=True,
        workers=2
    )
    if result2:
        all_results.append(result2)
    
    # 测试缓存效果
    test_cache_effectiveness()
    
    # 测试并发性能
    test_concurrent_requests()
    
    # 生成测试报告
    print(f"\n{'='*60}")
    print("性能优化测试报告")
    print(f"{'='*60}")
    
    if len(all_results) >= 2:
        # 比较有音频和无音频的性能差异
        no_audio = all_results[0]
        with_audio = all_results[1]
        
        print(f"\n音频合成对性能的影响:")
        print(f"无音频平均时间: {no_audio['avg_time']:.2f}s")
        print(f"有音频平均时间: {with_audio['avg_time']:.2f}s")
        print(f"时间增加: {with_audio['avg_time'] - no_audio['avg_time']:.2f}s")
        print(f"性能下降: {(with_audio['avg_time']/no_audio['avg_time'] - 1)*100:.1f}%")
    
    # 优化建议
    print(f"\n{'='*60}")
    print("优化建议:")
    print(f"{'='*60}")
    print("1. 缓存策略:")
    print("   - RAG结果缓存5分钟")
    print("   - LLM结果缓存10分钟") 
    print("   - TTS结果缓存30分钟")
    print("   - 完整响应缓存5分钟")
    print("\n2. 并行化:")
    print("   - RAG检索和会话历史获取并行执行")
    print("   - 支持并发请求处理")
    print("\n3. 性能监控:")
    print("   - 实时记录API调用时间")
    print("   - 缓存命中率统计")
    print("   - 错误率监控")
    print("\n4. 可配置参数:")
    print("   - 缓存TTL可调整")
    print("   - 并发数可配置")
    print("   - 超时时间可设置")

if __name__ == "__main__":
    main()