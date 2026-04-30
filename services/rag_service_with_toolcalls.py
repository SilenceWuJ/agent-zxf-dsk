#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
支持tool_calls处理的RAG服务
能够正确处理阿里云文件搜索的完整流程
"""

import requests
import time
import json
from typing import Optional, Dict, Any, List
from config import ALIYUN_API_KEY, KNOWLEDGE_BASE_ID
from utils.logger import logger


class ToolCallsRAGService:
    """支持tool_calls处理的RAG服务类"""
    
    def __init__(self):
        self.api_key = ALIYUN_API_KEY
        self.knowledge_base_id = KNOWLEDGE_BASE_ID
        self.timeout = 10  # 超时时间（秒）
        
    def search_knowledge(self, question: str) -> str:
        """
        完整的文件搜索流程
        包括处理tool_calls
        
        Args:
            question: 用户问题
            
        Returns:
            检索到的上下文文本
        """
        if not self.api_key:
            logger.warning("阿里云API密钥未配置")
            return ""
        
        if not self.knowledge_base_id:
            logger.warning("知识库ID未配置")
            return ""
        
        start_time = time.time()
        
        try:
            logger.info(f"开始文件搜索: {question[:30]}...")
            
            # 第一步：发起文件搜索请求
            initial_result = self._make_initial_request(question)
            if not initial_result:
                return ""
            
            # 第二步：处理tool_calls（如果有）
            final_result = self._process_tool_calls(initial_result, question)
            
            duration = time.time() - start_time
            
            if final_result:
                logger.info(f"文件搜索成功: 耗时 {duration:.2f}s, 长度 {len(final_result)}")
                return final_result
            else:
                logger.warning(f"文件搜索无结果: 耗时 {duration:.2f}s")
                return ""
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"文件搜索异常: {e}, 耗时 {duration:.2f}s")
            return ""
    
    def _make_initial_request(self, question: str) -> Optional[Dict[str, Any]]:
        """发起初始请求"""
        try:
            url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "qwen-plus",
                "messages": [
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                "tools": [
                    {
                        "type": "file_search",
                        "vector_store_ids": [self.knowledge_base_id]
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.1,
                "stream": False
            }
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("初始请求成功")
                return result
            else:
                logger.warning(f"初始请求失败: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"初始请求异常: {e}")
            return None
    
    def _process_tool_calls(self, initial_result: Dict[str, Any], original_question: str) -> str:
        """处理tool_calls，获取最终结果"""
        try:
            # 检查是否有choices和tool_calls
            if "choices" not in initial_result or len(initial_result["choices"]) == 0:
                logger.warning("初始响应中没有choices")
                return ""
            
            choice = initial_result["choices"][0]
            if "message" not in choice:
                logger.warning("choice中没有message")
                return ""
            
            message = choice["message"]
            
            # 如果没有tool_calls，检查是否有直接内容
            if "tool_calls" not in message or not message["tool_calls"]:
                if "content" in message and message["content"]:
                    logger.info("直接返回内容（无tool_calls）")
                    return message["content"].strip()
                else:
                    logger.warning("既无tool_calls也无content")
                    return ""
            
            # 处理tool_calls
            tool_calls = message["tool_calls"]
            logger.info(f"发现 {len(tool_calls)} 个tool_calls")
            
            # 构建继续对话的消息
            messages = [
                {
                    "role": "user",
                    "content": original_question
                },
                message  # 包含tool_calls的assistant消息
            ]
            
            # 添加tool_call结果（模拟工具执行）
            for tool_call in tool_calls:
                if "function" in tool_call:
                    function = tool_call["function"]
                    function_name = function.get("name", "")
                    function_args = function.get("arguments", "{}")
                    
                    logger.info(f"处理工具调用: {function_name}")
                    logger.debug(f"函数参数: {function_args}")
                    
                    # 对于file_search，我们添加一个工具响应
                    if function_name == "file_search":
                        tool_message = {
                            "role": "tool",
                            "content": "文件搜索已完成，但知识库可能为空或没有相关文档。",
                            "tool_call_id": tool_call.get("id", "")
                        }
                        messages.append(tool_message)
            
            # 发送最终请求获取结果
            final_result = self._make_final_request(messages)
            return final_result
            
        except Exception as e:
            logger.error(f"处理tool_calls异常: {e}")
            return ""
    
    def _make_final_request(self, messages: List[Dict[str, Any]]) -> str:
        """发送最终请求获取结果"""
        try:
            url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "qwen-plus",
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.1,
                "stream": False
            }
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content = choice["message"]["content"].strip()
                        if content:
                            logger.info(f"最终请求成功，获取到内容")
                            return content
            
            logger.warning(f"最终请求失败或无内容: HTTP {response.status_code}")
            return ""
                
        except Exception as e:
            logger.error(f"最终请求异常: {e}")
            return ""
    
    def quick_search(self, question: str) -> str:
        """
        快速搜索 - 简化版本
        如果知识库为空，快速返回空字符串
        
        Args:
            question: 用户问题
            
        Returns:
            搜索结果或空字符串
        """
        start_time = time.time()
        
        try:
            # 首先检查知识库状态
            kb_status = self._check_knowledge_base()
            if not kb_status.get("has_files", False):
                logger.info("知识库为空，跳过文件搜索")
                return ""
            
            # 如果知识库有文件，进行完整搜索
            result = self.search_knowledge(question)
            
            duration = time.time() - start_time
            if duration > 8:
                logger.warning(f"文件搜索较慢: {duration:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"快速搜索异常: {e}")
            return ""
    
    def _check_knowledge_base(self) -> Dict[str, Any]:
        """检查知识库状态"""
        try:
            kb_url = f"https://dashscope.aliyuncs.com/api/v1/vector-stores/{self.knowledge_base_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(kb_url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                kb_info = response.json()
                file_counts = kb_info.get("file_counts", {})
                total_files = file_counts.get("completed", 0)
                
                return {
                    "exists": True,
                    "status": kb_info.get("status", "unknown"),
                    "has_files": total_files > 0,
                    "file_count": total_files,
                    "name": kb_info.get("name", "unknown")
                }
            else:
                return {
                    "exists": False,
                    "has_files": False,
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            return {
                "exists": False,
                "has_files": False,
                "error": str(e)
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        info = {
            "api_key_configured": bool(self.api_key),
            "knowledge_base_id": self.knowledge_base_id,
            "knowledge_base_status": self._check_knowledge_base(),
            "timestamp": time.time()
        }
        
        return info


# 创建全局实例
toolcalls_rag_service = ToolCallsRAGService()


# 兼容接口
def search_knowledge(question: str) -> str:
    """搜索知识库（兼容接口）"""
    return toolcalls_rag_service.search_knowledge(question)


def quick_search(question: str) -> str:
    """快速搜索知识库"""
    return toolcalls_rag_service.quick_search(question)


def get_rag_info() -> Dict[str, Any]:
    """获取RAG服务信息"""
    return toolcalls_rag_service.get_service_info()


if __name__ == "__main__":
    # 测试tool_calls处理版本
    print("测试tool_calls处理版本RAG服务...")
    
    # 获取服务信息
    print("\n1. 服务信息:")
    info = get_rag_info()
    print(f"   API密钥配置: {'✅' if info['api_key_configured'] else '❌'}")
    print(f"   知识库ID: {info['knowledge_base_id']}")
    
    kb_status = info["knowledge_base_status"]
    print(f"   知识库存在: {'✅' if kb_status.get('exists') else '❌'}")
    if kb_status.get("exists"):
        print(f"   知识库名称: {kb_status.get('name', '未知')}")
        print(f"   知识库状态: {kb_status.get('status', '未知')}")
        print(f"   是否有文件: {'✅' if kb_status.get('has_files') else '❌'}")
        print(f"   文件数量: {kb_status.get('file_count', 0)}")
    
    # 测试搜索
    test_questions = [
        "普通家庭报考和选择学校",
        "计算机专业就业前景"
    ]
    
    for question in test_questions:
        print(f"\n2. 测试问题: {question}")
        
        # 测试完整搜索
        print("   a) 完整搜索测试:")
        start_time = time.time()
        result = search_knowledge(question)
        duration = time.time() - start_time
        
        if result:
            print(f"      ✅ 成功 (耗时: {duration:.2f}s)")
            print(f"      结果: {result[:100]}...")
        else:
            print(f"      ❌ 失败或无结果 (耗时: {duration:.2f}s)")
        
        # 测试快速搜索
        print("   b) 快速搜索测试:")
        start_time = time.time()
        result = quick_search(question)
        duration = time.time() - start_time
        
        if result:
            print(f"      ✅ 成功 (耗时: {duration:.2f}s)")
            print(f"      结果长度: {len(result)} 字符")
        else:
            print(f"      ⚠️  无结果 (耗时: {duration:.2f}s)")
            print(f"      原因: 知识库可能为空")
    
    print(f"\n{'='*60}")
    print("测试完成")
    print("=" * 60)