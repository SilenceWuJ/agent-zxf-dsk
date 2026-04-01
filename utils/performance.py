#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能分析和优化工具
"""

import time
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from typing import Dict, List, Any, Optional
import statistics

from utils.logger import logger


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {}
        self.lock = threading.Lock()
        
    def start_timer(self, name: str):
        """开始计时"""
        with self.lock:
            self.metrics[name] = {
                'start': time.time(),
                'end': None,
                'duration': None
            }
    
    def end_timer(self, name: str):
        """结束计时"""
        with self.lock:
            if name in self.metrics and self.metrics[name]['end'] is None:
                self.metrics[name]['end'] = time.time()
                self.metrics[name]['duration'] = (
                    self.metrics[name]['end'] - self.metrics[name]['start']
                )
    
    def get_duration(self, name: str) -> Optional[float]:
        """获取持续时间"""
        with self.lock:
            if name in self.metrics and self.metrics[name]['duration'] is not None:
                return self.metrics[name]['duration']
        return None
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        with self.lock:
            summary = {}
            for name, metric in self.metrics.items():
                if metric['duration'] is not None:
                    summary[name] = {
                        'duration': metric['duration'],
                        'start': metric['start'],
                        'end': metric['end']
                    }
            return summary
    
    def reset(self):
        """重置监控器"""
        with self.lock:
            self.metrics = {}


def time_it(func):
    """函数执行时间装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"函数 {func.__name__} 执行时间: {duration:.3f}秒")
        
        # 如果执行时间超过阈值，记录警告
        if duration > 5.0:
            logger.warning(f"函数 {func.__name__} 执行时间过长: {duration:.3f}秒")
        
        return result
    return wrapper


class APIOptimizer:
    """API调用优化器"""
    
    def __init__(self, max_workers: int = 3):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.cache = {}
        self.cache_lock = threading.Lock()
        self.cache_ttl = 300  # 缓存有效期5分钟
        
    def parallel_call(self, tasks: List[Dict]) -> Dict[str, Any]:
        """
        并行调用多个API
        
        Args:
            tasks: 任务列表，每个任务包含:
                - name: 任务名称
                - func: 要执行的函数
                - args: 函数参数
                - kwargs: 函数关键字参数
        
        Returns:
            包含所有任务结果的字典
        """
        results = {}
        futures = {}
        
        # 提交所有任务
        for task in tasks:
            future = self.executor.submit(task['func'], *task.get('args', []), **task.get('kwargs', {}))
            futures[future] = task['name']
        
        # 收集结果
        for future in as_completed(futures):
            task_name = futures[future]
            try:
                results[task_name] = future.result()
            except Exception as e:
                logger.error(f"任务 {task_name} 执行失败: {e}")
                results[task_name] = None
        
        return results
    
    def cached_call(self, cache_key: str, func, *args, **kwargs):
        """
        带缓存的函数调用
        
        Args:
            cache_key: 缓存键
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
        
        Returns:
            函数执行结果
        """
        current_time = time.time()
        
        # 检查缓存
        with self.cache_lock:
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if current_time - timestamp < self.cache_ttl:
                    logger.info(f"缓存命中: {cache_key}")
                    return cached_data
        
        # 执行函数
        result = func(*args, **kwargs)
        
        # 更新缓存
        with self.cache_lock:
            self.cache[cache_key] = (result, current_time)
        
        return result
    
    def clear_cache(self, prefix: str = None):
        """清理缓存"""
        with self.cache_lock:
            if prefix:
                keys_to_delete = [k for k in self.cache.keys() if k.startswith(prefix)]
                for key in keys_to_delete:
                    del self.cache[key]
                logger.info(f"清理缓存前缀: {prefix}, 删除 {len(keys_to_delete)} 个条目")
            else:
                self.cache.clear()
                logger.info("清理所有缓存")
    
    def shutdown(self):
        """关闭执行器"""
        self.executor.shutdown(wait=True)


def analyze_api_performance(api_calls: List[Dict]) -> Dict[str, Any]:
    """
    分析API调用性能
    
    Args:
        api_calls: API调用记录列表，每个记录包含:
            - name: API名称
            - duration: 调用时长
            - success: 是否成功
            - timestamp: 时间戳
    
    Returns:
        性能分析报告
    """
    if not api_calls:
        return {"error": "没有API调用记录"}
    
    # 按API名称分组
    api_groups = {}
    for call in api_calls:
        name = call['name']
        if name not in api_groups:
            api_groups[name] = []
        api_groups[name].append(call)
    
    # 计算统计信息
    report = {
        "total_calls": len(api_calls),
        "apis": {},
        "summary": {}
    }
    
    for api_name, calls in api_groups.items():
        durations = [call['duration'] for call in calls if call.get('success', True)]
        success_count = sum(1 for call in calls if call.get('success', True))
        failure_count = len(calls) - success_count
        
        if durations:
            report["apis"][api_name] = {
                "call_count": len(calls),
                "success_rate": success_count / len(calls) * 100,
                "avg_duration": statistics.mean(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "p95_duration": statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else max(durations),
                "failure_count": failure_count
            }
    
    # 总体统计
    all_durations = [call['duration'] for call in api_calls if call.get('success', True)]
    if all_durations:
        report["summary"] = {
            "total_duration": sum(all_durations),
            "avg_duration": statistics.mean(all_durations),
            "max_duration": max(all_durations),
            "success_rate": sum(1 for call in api_calls if call.get('success', True)) / len(api_calls) * 100
        }
    
    return report


# 全局性能监控器
monitor = PerformanceMonitor()
optimizer = APIOptimizer()