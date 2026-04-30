#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复版RAG服务
- 修复API参数错误
- 使用正确的端点和格式
- 优化超时设置
"""

import requests
import time
import json
from typing import Optional, Dict, Any
from config import ALIYUN_API_KEY, KNOWLEDGE_BASE_ID
from utils.logger import logger


class FixedRAGService:
    """修复版RAG服务类"""
    
    def __init__(self):
        self.api_key = ALIYUN_API_KEY
        self.knowledge_base_id = KNOWLEDGE_BASE_ID
        self.timeout = 8  # 超时时间（秒）
        
    def search_knowledge(self, question: str) -> str:
        """
        搜索知识库 - 使用正确的API格式
        
        Args:
            question: 用户问题
            
        Returns:
            检索到的上下文文本
        """
        if not self.api_key:
            logger.warning("阿里云API密钥未配置，跳过知识库检索")
            return ""
        
        if not self.knowledge_base_id:
            logger.warning("知识库ID未配置，跳过知识库检索")
            return ""
        
        start_time = time.time()
        
        try:
            logger.info(f"RAG检索: {question[:30]}...")
            
            # 使用正确的API端点和格式
            # 阿里云百炼Responses API的正确格式
            url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 正确的请求格式 - 确保最后一个消息的角色是"user"
            payload = {
                "model": "qwen-plus",
                "messages": [
                    {
                        "role": "user",  # 第一个消息必须是user
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
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                answer = self._extract_answer(result)
                
                if answer:
                    logger.info(f"RAG检索成功: 耗时 {duration:.2f}s, 长度 {len(answer)}")
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
                    return content.strip()
            
            # 备用格式: output.text
            if "output" in result and "text" in result["output"]:
                content = result["output"]["text"]
                return content.strip()
            
            # 尝试解析其他格式
            return self._try_other_formats(result)
            
        except Exception as e:
            logger.error(f"提取回答失败: {e}")
            return ""
    
    def _try_other_formats(self, result: Dict[str, Any]) -> str:
        """尝试其他响应格式"""
        # 格式1: output[0].content[0].text (Responses API格式)
        if "output" in result and isinstance(result["output"], list):
            for output_item in result["output"]:
                if "content" in output_item and isinstance(output_item["content"], list):
                    for content_item in output_item["content"]:
                        if content_item.get("type") == "output_text" and "text" in content_item:
                            return content_item["text"].strip()
        
        # 格式2: 递归搜索所有文本字段
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
            # 优先选择包含"output"或"content"的文本
            for path, text in all_texts:
                if "output" in path.lower() or "content" in path.lower():
                    logger.debug(f"找到文本字段: {path}")
                    return text.strip()
            
            # 返回第一个文本
            logger.debug(f"找到文本字段: {all_texts[0][0]}")
            return all_texts[0][1].strip()
        
        logger.warning(f"未知的响应格式: {json.dumps(result, ensure_ascii=False)[:200]}...")
        return ""
    
    def simple_search(self, question: str) -> str:
        """
        简单搜索 - 不使用文件搜索，只调用基础模型
        
        Args:
            question: 用户问题
            
        Returns:
            模型生成的回答
        """
        if not self.api_key:
            return ""
        
        start_time = time.time()
        
        try:
            logger.info(f"简单搜索: {question[:30]}...")
            
            # 使用简单的文本生成API
            url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 简单的对话格式，不使用文件搜索
            payload = {
                "model": "qwen-plus",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个高考志愿咨询助手，请简要回答用户关于高考志愿的问题。"
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                "max_tokens": 300,
                "temperature": 0.3,
                "stream": False
            }
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=5  # 更短的超时
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        answer = choice["message"]["content"].strip()
                        logger.info(f"简单搜索成功: 耗时 {duration:.2f}s, 长度 {len(answer)}")
                        return answer
            
            logger.warning(f"简单搜索失败: HTTP {response.status_code}, 耗时 {duration:.2f}s")
            return ""
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"简单搜索异常: {e}, 耗时 {duration:.2f}s")
            return ""
    
    def test_api(self) -> Dict[str, Any]:
        """测试API连接和格式"""
        test_results = {
            "api_key_configured": bool(self.api_key),
            "knowledge_base_configured": bool(self.knowledge_base_id),
            "endpoints": {}
        }
        
        if not self.api_key:
            return test_results
        
        # 测试端点1: 兼容模式chat/completions
        endpoint1 = {
            "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "payload": {
                "model": "qwen-plus",
                "messages": [
                    {
                        "role": "user",
                        "content": "测试"
                    }
                ],
                "max_tokens": 10
            }
        }
        
        # 测试端点2: Responses API
        endpoint2 = {
            "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/responses",
            "payload": {
                "model": "qwen-plus",
                "input": "测试",
                "tools": [
                    {
                        "type": "file_search",
                        "vector_store_ids": [self.knowledge_base_id] if self.knowledge_base_id else []
                    }
                ]
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        for name, endpoint in [("chat/completions", endpoint1), ("responses", endpoint2)]:
            try:
                start_time = time.time()
                response = requests.post(
                    endpoint["url"],
                    headers=headers,
                    json=endpoint["payload"],
                    timeout=10
                )
                duration = time.time() - start_time
                
                test_results["endpoints"][name] = {
                    "status_code": response.status_code,
                    "duration": duration,
                    "success": response.status_code == 200
                }
                
                if response.status_code != 200:
                    test_results["endpoints"][name]["error"] = response.text[:200]
                    
            except Exception as e:
                test_results["endpoints"][name] = {
                    "error": str(e),
                    "success": False
                }
        
        return test_results


# 创建全局实例
fixed_rag_service = FixedRAGService()


# 兼容接口
def search_knowledge(question: str) -> str:
    """搜索知识库（兼容接口）"""
    return fixed_rag_service.search_knowledge(question)


def simple_search(question: str) -> str:
    """简单搜索（不使用文件搜索）"""
    return fixed_rag_service.simple_search(question)


def test_rag_api() -> Dict[str, Any]:
    """测试RAG API"""
    return fixed_rag_service.test_api()


if __name__ == "__main__":
    # 测试修复版RAG服务
    print("测试修复版RAG服务...")
    
    # 测试API连接
    print("\n1. 测试API连接...")
    test_results = test_rag_api()
    print(f"API密钥配置: {'✅' if test_results['api_key_configured'] else '❌'}")
    print(f"知识库配置: {'✅' if test_results['knowledge_base_configured'] else '❌'}")
    
    for endpoint, result in test_results["endpoints"].items():
        status = "✅" if result.get("success") else "❌"
        print(f"{endpoint}: {status} (状态码: {result.get('status_code', 'N/A')})")
        if "error" in result:
            print(f"   错误: {result['error']}")
    
    # 测试搜索
    test_questions = [
        "普通家庭报考和选择学校",
        "什么是人工智能？"
    ]
    
    for question in test_questions:
        print(f"\n2. 测试问题: {question}")
        
        # 测试文件搜索
        print("   a) 文件搜索测试:")
        start_time = time.time()
        result = search_knowledge(question)
        duration = time.time() - start_time
        
        if result:
            print(f"      ✅ 成功 (耗时: {duration:.2f}s)")
            print(f"      结果: {result[:100]}...")
        else:
            print(f"      ❌ 失败 (耗时: {duration:.2f}s)")
        
        # 测试简单搜索
        print("   b) 简单搜索测试:")
        start_time = time.time()
        result = simple_search(question)
        duration = time.time() - start_time
        
        if result:
            print(f"      ✅ 成功 (耗时: {duration:.2f}s)")
            print(f"      结果: {result[:100]}...")
        else:
            print(f"      ❌ 失败 (耗时: {duration:.2f}s)")