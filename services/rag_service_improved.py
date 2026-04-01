#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
改进的RAG服务
- 更好的错误处理
- 详细的日志记录
- 支持备用方案
"""

import requests
import json
import time
from typing import Optional, Dict, Any
from config import ALIYUN_API_KEY, ALIYUN_BASE_URL, KNOWLEDGE_BASE_ID
from utils.logger import logger


class RAGService:
    """RAG服务类"""
    
    def __init__(self):
        self.api_key = ALIYUN_API_KEY
        self.base_url = ALIYUN_BASE_URL
        self.knowledge_base_id = KNOWLEDGE_BASE_ID
        self.timeout = 15  # 超时时间（秒）
        self.max_retries = 2  # 最大重试次数
        
    def search_knowledge(self, question: str) -> str:
        """
        搜索知识库
        
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
        
        # 记录开始时间
        start_time = time.time()
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"开始RAG检索 (尝试 {attempt + 1}/{self.max_retries + 1}): {question[:50]}...")
                
                # 构建请求
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # 尝试不同的API端点
                endpoints = [
                    f"{self.base_url}/responses",  # 兼容模式端点
                    "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",  # 文本生成端点
                ]
                
                payload = {
                    "model": "qwen-plus",
                    "input": {
                        "messages": [
                            {
                                "role": "user",
                                "content": question
                            }
                        ]
                    },
                    "parameters": {
                        "result_format": "message"
                    }
                }
                
                # 如果有知识库ID，添加文件搜索工具
                if self.knowledge_base_id:
                    payload["tools"] = [
                        {
                            "type": "file_search",
                            "vector_store_ids": [self.knowledge_base_id]
                        }
                    ]
                
                # 尝试不同的端点
                response_text = ""
                for endpoint in endpoints:
                    try:
                        logger.debug(f"尝试端点: {endpoint}")
                        response = requests.post(
                            endpoint,
                            headers=headers,
                            json=payload,
                            timeout=self.timeout
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            response_text = self._extract_response_text(result)
                            if response_text:
                                break  # 成功获取响应，跳出循环
                        else:
                            logger.warning(f"端点 {endpoint} 返回错误: HTTP {response.status_code}")
                            logger.debug(f"响应内容: {response.text[:200]}")
                    except requests.exceptions.Timeout:
                        logger.warning(f"端点 {endpoint} 请求超时")
                    except Exception as e:
                        logger.warning(f"端点 {endpoint} 请求异常: {e}")
                
                # 如果获取到响应文本
                if response_text:
                    duration = time.time() - start_time
                    logger.info(f"RAG检索成功: 耗时 {duration:.2f}s, 文本长度 {len(response_text)}")
                    logger.debug(f"检索结果: {response_text[:200]}...")
                    return response_text
                
                # 如果所有端点都失败，尝试备用方案
                if attempt == self.max_retries:
                    logger.warning("所有API端点都失败，使用备用方案")
                    return self._fallback_search(question)
                
                # 重试前等待
                if attempt < self.max_retries:
                    wait_time = 1 * (attempt + 1)  # 指数退避
                    logger.info(f"等待 {wait_time}s 后重试...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                logger.error(f"RAG检索异常 (尝试 {attempt + 1}): {e}")
                if attempt == self.max_retries:
                    logger.warning("达到最大重试次数，使用备用方案")
                    return self._fallback_search(question)
                
                # 重试前等待
                if attempt < self.max_retries:
                    wait_time = 1 * (attempt + 1)
                    logger.info(f"等待 {wait_time}s 后重试...")
                    time.sleep(wait_time)
        
        # 所有尝试都失败
        return ""
    
    def _extract_response_text(self, result: Dict[str, Any]) -> str:
        """从API响应中提取文本"""
        try:
            # 检查是否有错误
            if "error" in result:
                error_msg = result["error"].get("message", "未知错误")
                logger.warning(f"API返回错误: {error_msg}")
                
                # 如果是内容安全问题，返回空字符串
                if "inappropriate content" in error_msg.lower():
                    logger.warning("内容被标记为不合适，跳过知识库检索")
                    return ""
                return ""
            
            # 检查状态
            if result.get("status") == "failed":
                logger.warning(f"API请求失败: {result.get('error', {}).get('message', '未知错误')}")
                return ""
            
            # 格式1: Responses API格式 - output[0].content[0].text
            if "output" in result and isinstance(result["output"], list):
                for output_item in result["output"]:
                    if "content" in output_item and isinstance(output_item["content"], list):
                        for content_item in output_item["content"]:
                            if content_item.get("type") == "output_text" and "text" in content_item:
                                return content_item["text"]
            
            # 格式2: output.text (简单格式)
            if "output" in result and "text" in result["output"]:
                return result["output"]["text"]
            
            # 格式3: choices[0].message.content (OpenAI兼容格式)
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
            
            # 格式4: output.choices[0].message.content
            if "output" in result and "choices" in result["output"]:
                if len(result["output"]["choices"]) > 0:
                    choice = result["output"]["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        return choice["message"]["content"]
            
            # 格式5: 递归搜索所有文本字段
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
                # 优先选择output_text类型的文本
                for path, text in all_texts:
                    if "output" in path.lower() and "text" in path.lower():
                        logger.debug(f"找到文本字段: {path}")
                        return text
                
                # 如果没有output_text，返回第一个文本
                logger.debug(f"找到文本字段: {all_texts[0][0]}")
                return all_texts[0][1]
            
            # 如果以上格式都不匹配，记录警告
            logger.warning(f"未知的响应格式: {json.dumps(result, ensure_ascii=False)[:200]}...")
            return ""
            
        except Exception as e:
            logger.error(f"提取响应文本失败: {e}")
            return ""
    
    def _fallback_search(self, question: str) -> str:
        """备用搜索方案"""
        logger.info(f"使用备用方案搜索: {question[:50]}...")
        
        # 这里可以实现本地知识库搜索或其他备用方案
        # 目前返回空字符串，让LLM基于自身知识回答
        
        # 可以根据问题关键词返回一些预设的上下文
        keywords = {
            "计算机": "计算机专业是当前就业前景最好的专业之一，涉及软件开发、人工智能、数据分析等多个方向。",
            "考研": "考研需要提前准备，包括选择专业和院校、复习公共课和专业课、准备复试等环节。",
            "就业": "就业前景需要考虑行业发展趋势、个人技能匹配度、薪资待遇等多个因素。",
            "专业": "选择专业需要考虑个人兴趣、就业前景、学习难度、家庭经济条件等因素。",
            "大学": "选择大学需要考虑学校排名、专业实力、地理位置、就业资源等因素。"
        }
        
        for keyword, context in keywords.items():
            if keyword in question:
                logger.info(f"备用方案匹配关键词: {keyword}")
                return context
        
        return ""
    
    def test_connection(self) -> bool:
        """测试API连接"""
        if not self.api_key:
            logger.error("阿里云API密钥未配置")
            return False
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 简单的测试请求
            test_payload = {
                "model": "qwen-plus",
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "测试"
                        }
                    ]
                }
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=test_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("阿里云API连接测试成功")
                return True
            else:
                logger.error(f"阿里云API连接测试失败: HTTP {response.status_code}")
                logger.debug(f"响应: {response.text[:200]}")
                return False
                
        except Exception as e:
            logger.error(f"阿里云API连接测试异常: {e}")
            return False


# 创建全局实例
rag_service = RAGService()


# 兼容旧接口的函数
def search_knowledge(question: str) -> str:
    """搜索知识库（兼容旧接口）"""
    return rag_service.search_knowledge(question)


if __name__ == "__main__":
    # 测试RAG服务
    print("测试RAG服务...")
    
    # 测试连接
    print("测试API连接...")
    if rag_service.test_connection():
        print("✅ API连接成功")
    else:
        print("❌ API连接失败")
    
    # 测试搜索
    test_questions = [
        "计算机专业就业前景怎么样？",
        "如何准备考研？",
        "什么是人工智能？"
    ]
    
    for question in test_questions:
        print(f"\n测试问题: {question}")
        start_time = time.time()
        result = rag_service.search_knowledge(question)
        duration = time.time() - start_time
        
        if result:
            print(f"✅ 搜索成功 (耗时: {duration:.2f}s)")
            print(f"结果: {result[:100]}...")
        else:
            print(f"❌ 搜索失败 (耗时: {duration:.2f}s)")