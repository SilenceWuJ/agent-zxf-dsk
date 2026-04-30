#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阿里云百炼应用ID调用服务
使用Application.call方式调用
"""

import os
from dotenv import load_dotenv
import json
from http import HTTPStatus
from typing import Dict, Any, Optional
import time
load_dotenv()

app_id =os.getenv("ALIYUN_APP_ID")
knowledge_id = os.getenv("KNOWLEDGE_BASE_ID")

APP_ID = os.getenv("ALIYUN_APP_ID_J")
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID_J")

try:
    from dashscope import Application
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False

from utils.logger import logger
from utils.cache_improved import get_cache, set_cache


def call_application(
    prompt: str,
    app_id: Optional[str] = None,
    api_key: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    调用阿里云百炼应用
    
    Args:
        prompt: 用户输入的提示词
        app_id: 应用ID，如果为None则使用环境变量中的值
        api_key: API密钥，如果为None则使用环境变量中的值
        use_cache: 是否使用缓存
    
    Returns:
        包含响应结果的字典
    """
    if not DASHSCOPE_AVAILABLE:
        logger.error("dashscope模块未安装，请运行: pip install dashscope")
        return {
            "success": False,
            "error": "dashscope模块未安装",
            "output": None
        }
    
    # 获取配置
    if app_id is None:
        app_id = os.getenv("ALIYUN_APP_ID")

    
    if api_key is None:
        api_key = os.getenv("ALIYUN_API_KEY")
    
    if not app_id:
        logger.error("未配置阿里云应用ID")
        return {
            "success": False,
            "error": "未配置阿里云应用ID",
            "output": None
        }
    
    if not api_key:
        logger.error("未配置阿里云API密钥")
        return {
            "success": False,
            "error": "未配置阿里云API密钥",
            "output": None
        }
    
    # 生成缓存键
    cache_key = f"app_call:{app_id}:{hash(prompt)}"
    
    # 尝试从缓存获取
    if use_cache:
        cached_result = get_cache(cache_key)
        if cached_result:
            logger.info(f"应用调用缓存命中: {prompt[:30]}...")
            return {
                "success": True,
                "output": cached_result,
                "cached": True,
                "request_id": "cached"
            }
    
    logger.info(f"调用阿里云应用ID: {app_id}, 提示词: {prompt[:50]}...")
    
    try:
        start_time = time.time()
        
        # 调用阿里云百炼应用，增加超时设置
        response = Application.call(
            api_key=api_key,
            app_id=app_id,
            prompt=prompt,
            timeout=30  # 增加超时时间到30秒
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"应用调用完成，耗时: {duration:.2f}秒，状态码: {response.status_code}")
        
        if response.status_code != HTTPStatus.OK:
            logger.error(f"应用调用失败: {response.message}, request_id={response.request_id}")
            return {
                "success": False,
                "error": response.message,
                "status_code": response.status_code,
                "request_id": response.request_id,
                "duration": duration
            }
        
        # 提取响应内容
        result = {
            "text": response.output.text if hasattr(response.output, 'text') else str(response.output),
            "request_id": response.request_id,
            "usage": getattr(response.usage, '__dict__', {}) if hasattr(response, 'usage') else {},
            "duration": duration
        }
        
        # 缓存结果（缓存10分钟）
        if use_cache:
            try:
                set_cache(cache_key, result, expire=600)
            except Exception as cache_err:
                logger.warning(f"写入应用调用缓存失败: {cache_err}")
        
        return {
            "success": True,
            "output": result,
            "cached": False,
            "request_id": response.request_id,
            "duration": duration
        }
        
    except Exception as e:
        logger.error(f"应用调用异常: {e}")
        return {
            "success": False,
            "error": str(e),
            "output": None
        }


def call_application_with_context(
    prompt: str,
    context: Optional[str] = None,
    history: Optional[list] = None,
    app_id: Optional[str] = None,
    api_key: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    调用阿里云百炼应用（带上下文和历史）
    
    Args:
        prompt: 用户输入的提示词
        context: 上下文信息（如知识库检索结果）
        history: 对话历史
        app_id: 应用ID
        api_key: API密钥
        use_cache: 是否使用缓存
    
    Returns:
        包含响应结果的字典
    """
    # 构建完整的提示词
    full_prompt = prompt
    
    if context:
        full_prompt = f"参考信息：{context}\n\n问题：{prompt}"
    
    if history:
        # 将历史对话格式化为文本
        history_text = "\n".join([
            f"用户：{h.get('user', '')}" if isinstance(h, dict) else str(h)
            for h in history[-5:]  # 只使用最近5条历史
        ])
        if history_text:
            full_prompt = f"对话历史：{history_text}\n\n{full_prompt}"
    
    # 调用应用
    return call_application(full_prompt, app_id, api_key, use_cache)



def call_pedu_application(
    prompt: str,
    context: Optional[str] = None,
    history: Optional[list] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    调用教育版阿里云百炼应用
    
    Args:
        prompt: 用户输入的提示词
        context: 上下文信息（如知识库检索结果）
        history: 对话历史
        use_cache: 是否使用缓存
    
    Returns:
        包含响应结果的字典
    """
    # 教育版特定的应用ID和知识库ID
    PEDU_APP_ID = APP_ID
    PEDU_KNOWLEDGE_BASE_ID = KNOWLEDGE_BASE_ID
    print("edu",PEDU_APP_ID,PEDU_KNOWLEDGE_BASE_ID)
    
    try:
        # 读取提示词模板文件
        import os
        template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'jiaoyuan.md')
        
        with open(template_path, 'r', encoding='utf-8') as f:
            system_prompt = f.read()
        
        # 构建完整的提示词（包含系统提示词和用户问题）
        full_prompt = f"{system_prompt}\n\n用户问题：{prompt}"
        
        # 如果有知识库ID，可以添加到提示词中
        if PEDU_KNOWLEDGE_BASE_ID:
            full_prompt = f"知识库ID: {PEDU_KNOWLEDGE_BASE_ID}\n\n{full_prompt}"
        
        if context:
            full_prompt = f"参考信息：{context}\n\n{full_prompt}"
        
        if history:
            # 将历史对话格式化为文本
            history_text = "\n".join([
                f"用户：{h.get('user', '')}" if isinstance(h, dict) else str(h)
                for h in history[-5:]  # 只使用最近5条历史
            ])
            if history_text:
                full_prompt = f"对话历史：{history_text}\n\n{full_prompt}"
        
        # 调用教育版应用
        return call_application(full_prompt, PEDU_APP_ID, None, use_cache)
        
    except Exception as e:
        logger.error(f"读取提示词模板失败: {e}")
        # 如果读取模板失败，使用简化的提示词
        full_prompt = prompt
        
        if PEDU_KNOWLEDGE_BASE_ID:
            full_prompt = f"知识库ID: {PEDU_KNOWLEDGE_BASE_ID}\n\n{full_prompt}"
        
        if context:
            full_prompt = f"参考信息：{context}\n\n问题：{full_prompt}"
        
        if history:
            history_text = "\n".join([
                f"用户：{h.get('user', '')}" if isinstance(h, dict) else str(h)
                for h in history[-5:]
            ])
            if history_text:
                full_prompt = f"对话历史：{history_text}\n\n{full_prompt}"
        
        return call_pedu_application(full_prompt, PEDU_APP_ID, None, use_cache)


def call_application_edu_with_context(
        prompt: str,
        context: Optional[str] = None,
        history: Optional[list] = None,
        app_id: Optional[str] = APP_ID,
        api_key: Optional[str] = None,
        use_cache: bool = True
) -> Dict[str, Any]:
    """
    调用阿里云百炼应用（带上下文和历史）

    Args:
        prompt: 用户输入的提示词
        context: 上下文信息（如知识库检索结果）
        history: 对话历史
        app_id: 应用ID
        api_key: API密钥
        use_cache: 是否使用缓存

    Returns:
        包含响应结果的字典
    """
    # 构建完整的提示词
    full_prompt = prompt

    if context:
        full_prompt = f"参考信息：{context}\n\n问题：{prompt}"

    if history:
        # 将历史对话格式化为文本
        history_text = "\n".join([
            f"用户：{h.get('user', '')}" if isinstance(h, dict) else str(h)
            for h in history[-5:]  # 只使用最近5条历史
        ])
        if history_text:
            full_prompt = f"对话历史：{history_text}\n\n{full_prompt}"

    # 调用应用
    return call_pedu_application(full_prompt, app_id, api_key, use_cache)


if __name__ == "__main__":
    # 测试应用调用
    # print("测试阿里云百炼应用调用...")
    #
    # # 测试基本调用
    # test_prompt = "你是谁？"
    # result = call_application(test_prompt)
    #
    # print(f"测试提示词: {test_prompt}")
    # print(f"调用结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    #
    # # 测试带上下文的调用
    # print("\n测试带上下文的调用...")
    # context = "这是一个测试上下文，包含一些相关信息。"
    # result_with_context = call_application_with_context(
    #     prompt="基于上面的信息，你有什么建议？",
    #     context=context
    # )
    #
    # print(f"带上下文调用结果: {json.dumps(result_with_context, ensure_ascii=False, indent=2)}")
    print("------------------")
    # 测试应用调用
    print("测试阿里云百炼应用调用...")

    # 测试基本调用
    test_prompt = "2026年AI迅速发展经济影响？"
    result = call_pedu_application(test_prompt)

    print(f"测试提示词: {test_prompt}")
    print(f"调用结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

    # 测试带上下文的调用
    print("\n测试带上下文的调用...")
    context = "这是一个测试上下文，包含一些相关信息。"
    result_with_context = call_application_edu_with_context(
        prompt="基于上面的信息，你有什么建议？",
        context=context
    )

    print(f"带上下文调用结果: {json.dumps(result_with_context, ensure_ascii=False, indent=2)}")
