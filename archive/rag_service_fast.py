#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速RAG服务 - 优化版本
- 修复API参数错误
- 减少响应时间
- 添加快速降级
"""

import requests
import time
import json
from typing import Optional, Dict, Any
from config import ALIYUN_API_KEY, KNOWLEDGE_BASE_ID
from utils.logger import logger


class FastRAGService:
    """快速RAG服务类"""
    
    def __init__(self):
        self.api_key = ALIYUN_API_KEY
        self.knowledge_base_id = KNOWLEDGE_BASE_ID
        self.timeout = 8  # 更短的超时时间（秒）
        self.max_retries = 1  # 减少重试次数
        
    def search_knowledge(self, question: str) -> str:
        """
        快速搜索知识库
        
        Args:
            question: 用户问题
            
        Returns:
            检索到的上下文文本（快速返回，失败时返回空字符串）
        """
        if not self.api_key:
            logger.warning("阿里云API密钥未配置，跳过知识库检索")
            return ""
        
        if not self.knowledge_base_id:
            logger.warning("知识库ID未配置，跳过知识库检索")
            return ""
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            logger.info(f"快速RAG检索: {question[:30]}...")
            
            # 使用正确的API端点和参数
            url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 正确的请求格式 - 使用messages数组
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
                "max_tokens": 500,  # 限制输出长度
                "temperature": 0.1,  # 降低随机性，提高速度
                "stream": False
            }
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                answer = self._extract_answer(result)
                
                if answer:
                    logger.info(f"RAG检索成功: 耗时 {duration:.2f}s, 文本长度 {len(answer)}")
                    return answer
                else:
                    logger.warning(f"RAG检索返回空结果: 耗时 {duration:.2f}s")
                    return ""
            else:
                logger.warning(f"RAG检索失败: HTTP {response.status_code}, 耗时 {duration:.2f}s")
                logger.debug(f"错误响应: {response.text[:200]}")
                return ""
                
        except requests.exceptions.Timeout:
            duration = time.time() - start_time
            logger.warning(f"RAG检索超时: 耗时 {duration:.2f}s")
            return ""
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"RAG检索异常: {e}, 耗时 {duration:.2f}s")
            return ""
    
    def _extract_answer(self, result: Dict[str, Any]) -> str:
        """从API响应中提取回答"""
        try:
            # 检查是否有错误
            if "error" in result:
                error_msg = result["error"].get("message", "未知错误")
                logger.warning(f"API返回错误: {error_msg}")
                return ""
            
            # 标准格式: choices[0].message.content
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]
                    # 提取前500个字符，避免过长
                    return content[:500].strip()
            
            # 备用格式: output.text
            if "output" in result and "text" in result["output"]:
                content = result["output"]["text"]
                return content[:500].strip()
            
            logger.warning(f"未知的响应格式: {json.dumps(result, ensure_ascii=False)[:200]}...")
            return ""
            
        except Exception as e:
            logger.error(f"提取回答失败: {e}")
            return ""
    
    def quick_search(self, question: str) -> str:
        """
        超快速搜索 - 5秒内必须返回
        
        Args:
            question: 用户问题
            
        Returns:
            检索结果或空字符串
        """
        start_time = time.time()
        
        try:
            # 设置更短的超时
            original_timeout = self.timeout
            self.timeout = 5
            
            result = self.search_knowledge(question)
            
            duration = time.time() - start_time
            if duration > 4.5:
                logger.warning(f"快速搜索接近超时: {duration:.2f}s")
            
            # 恢复原始超时设置
            self.timeout = original_timeout
            
            return result
            
        except Exception as e:
            logger.error(f"快速搜索异常: {e}")
            return ""


# 创建全局实例
fast_rag_service = FastRAGService()


# 兼容接口
def search_knowledge(question: str) -> str:
    """搜索知识库（兼容接口）"""
    return fast_rag_service.search_knowledge(question)


def quick_search(question: str) -> str:
    """快速搜索知识库"""
    return fast_rag_service.quick_search(question)


if __name__ == "__main__":
    # 测试快速RAG服务
    print("测试快速RAG服务...")
    
    test_questions = [
        "什么是人工智能？",
        "计算机专业就业前景怎么样？"
    ]
    
    for question in test_questions:
        print(f"\n测试问题: {question}")
        
        # 测试快速搜索
        print("1. 快速搜索测试:")
        start_time = time.time()
        result = quick_search(question)
        duration = time.time() - start_time
        
        if result:
            print(f"   ✅ 成功 (耗时: {duration:.2f}s)")
            print(f"   结果: {result[:100]}...")
        else:
            print(f"   ❌ 失败 (耗时: {duration:.2f}s)")
        
        # 测试普通搜索
        print("2. 普通搜索测试:")
        start_time = time.time()
        result = search_knowledge(question)
        duration = time.time() - start_time
        
        if result:
            print(f"   ✅ 成功 (耗时: {duration:.2f}s)")
            print(f"   结果长度: {len(result)} 字符")
        else:
            print(f"   ❌ 失败 (耗时: {duration:.2f}s)")