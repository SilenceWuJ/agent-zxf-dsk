#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速版本的应用入口
主要优化：
1. 使用快速RAG和LLM服务
2. 严格的超时控制
3. 快速降级方案
4. 性能监控和告警
"""

import os
import time
import uuid
import json
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeout
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

from services.rag_service_fast import search_knowledge, quick_search
from services.llm_service_fast import ask_llm, quick_ask
from services.session_service import get_session, save_session
from utils.cache_improved import get_cache, set_cache, clear_cache
from utils.performance import monitor, optimizer, time_it
from utils.logger import logger

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# ==================== 配置区域 ====================
# 性能配置
MAX_RESPONSE_TIME = 15  # 最大响应时间（秒）
RAG_TIMEOUT = 6  # RAG超时时间（秒）
LLM_TIMEOUT = 10  # LLM超时时间（秒）
CACHE_TTL = 300  # 缓存有效期（秒）

# 语音合成配置
TTS_FORMAT = "mp3"

# ==================== 核心函数 ====================

def fast_rag_search(question: str) -> str:
    """
    快速RAG搜索
    6秒内必须返回结果，否则返回空字符串
    """
    start_time = time.time()
    
    try:
        # 使用快速搜索
        result = quick_search(question)
        
        duration = time.time() - start_time
        if result:
            logger.info(f"快速RAG成功: 耗时 {duration:.2f}s, 长度 {len(result)}")
        else:
            logger.info(f"快速RAG无结果: 耗时 {duration:.2f}s")
        
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"快速RAG异常: {e}, 耗时 {duration:.2f}s")
        return ""


def fast_llm_generate(question: str, context: str, history: list) -> str:
    """
    快速LLM生成
    10秒内必须返回结果，否则返回备用回答
    """
    start_time = time.time()
    
    try:
        # 使用快速提问
        answer = quick_ask(question, context, history)
        
        duration = time.time() - start_time
        logger.info(f"快速LLM成功: 耗时 {duration:.2f}s, 长度 {len(answer)}")
        
        return answer
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"快速LLM异常: {e}, 耗时 {duration:.2f}s")
        return "我跟你说啊，这个问题需要点时间思考。要不你先问问别的？"


def parallel_fast_processing(question: str, session_id: str) -> dict:
    """
    并行快速处理
    总时间控制在15秒内
    """
    overall_start = time.time()
    results = {
        "rag_result": "",
        "llm_result": "",
        "session_id": session_id,
        "processing_time": 0,
        "warnings": []
    }
    
    try:
        # 获取会话历史（快速）
        history_start = time.time()
        history = get_session(session_id)
        history_time = time.time() - history_start
        
        if history_time > 1:
            logger.warning(f"获取会话历史较慢: {history_time:.2f}s")
        
        # 第一阶段：并行执行RAG和LLM准备
        with ThreadPoolExecutor(max_workers=2) as executor:
            # 提交RAG任务（6秒超时）
            rag_future = executor.submit(fast_rag_search, question)
            
            # 提交LLM任务（使用空上下文先准备）
            llm_future = executor.submit(fast_llm_generate, question, "", history)
            
            # 等待RAG结果（最多6秒）
            try:
                rag_result = rag_future.result(timeout=RAG_TIMEOUT)
                results["rag_result"] = rag_result
            except FutureTimeout:
                logger.warning("RAG任务超时，使用空上下文")
                results["warnings"].append("知识库检索超时")
            except Exception as e:
                logger.error(f"RAG任务异常: {e}")
                results["warnings"].append("知识库检索失败")
            
            # 如果有RAG结果，重新提交LLM任务
            if results["rag_result"]:
                llm_future.cancel()  # 取消之前的任务
                llm_future = executor.submit(fast_llm_generate, question, results["rag_result"], history)
            
            # 等待LLM结果（最多10秒）
            try:
                llm_result = llm_future.result(timeout=LLM_TIMEOUT)
                results["llm_result"] = llm_result
            except FutureTimeout:
                logger.warning("LLM任务超时，使用备用回答")
                results["llm_result"] = "我跟你说啊，这个问题有点复杂，让我再想想。或者你可以问个更具体的问题？"
                results["warnings"].append("AI思考超时")
            except Exception as e:
                logger.error(f"LLM任务异常: {e}")
                results["llm_result"] = "抱歉，AI张老师暂时无法回答。请稍后再试！"
                results["warnings"].append("AI生成失败")
        
        # 更新会话历史
        if history is not None and results["llm_result"]:
            try:
                history.append({"role": "user", "content": question})
                history.append({"role": "assistant", "content": results["llm_result"]})
                save_session(session_id, history)
            except Exception as e:
                logger.error(f"更新会话历史失败: {e}")
        
        # 计算总处理时间
        total_time = time.time() - overall_start
        results["processing_time"] = total_time
        
        # 性能检查
        if total_time > MAX_RESPONSE_TIME:
            logger.warning(f"处理时间超过阈值: {total_time:.2f}s > {MAX_RESPONSE_TIME}s")
            results["warnings"].append(f"响应较慢: {total_time:.2f}s")
        
        logger.info(f"并行处理完成: 总耗时 {total_time:.2f}s")
        
        return results
        
    except Exception as e:
        total_time = time.time() - overall_start
        logger.error(f"并行处理异常: {e}, 总耗时 {total_time:.2f}s")
        
        results["llm_result"] = "抱歉，系统暂时无法处理您的请求。请稍后再试！"
        results["processing_time"] = total_time
        results["warnings"].append("系统处理异常")
        
        return results


# ==================== 路由函数 ====================

@app.route("/chat", methods=["POST"])
def chat():
    """快速聊天接口 - 15秒内必须响应"""
    start_time = time.time()
    
    try:
        data = request.get_json()
        user_question = data.get("question", "").strip()
        need_audio = data.get("need_audio", False)  # 默认关闭音频，提高速度
        
        if not user_question:
            return jsonify({
                "error": "请输入问题",
                "answer": "请告诉我你想了解什么专业或院校信息？"
            }), 400
        
        # 生成会话ID
        session_id = data.get("session_id", str(uuid.uuid4()))
        
        # 检查缓存
        cache_key = f"fast:chat:{user_question}"
        cached_response = get_cache(cache_key)
        if cached_response:
            logger.info(f"快速缓存命中: {user_question[:30]}...")
            cached_response["cached"] = True
            cached_response["session_id"] = session_id
            return jsonify(cached_response)
        
        # 执行快速处理
        logger.info(f"开始快速处理: {user_question[:50]}...")
        processing_results = parallel_fast_processing(user_question, session_id)
        
        # 构建响应
        response_data = {
            "answer": processing_results["llm_result"],
            "session_id": session_id,
            "processing_time": processing_results["processing_time"],
            "cached": False
        }
        
        # 添加警告信息（如果有）
        if processing_results.get("warnings"):
            response_data["warnings"] = processing_results["warnings"]
        
        # 缓存响应（5分钟）
        set_cache(cache_key, response_data, expire=CACHE_TTL)
        
        # 最终性能检查
        total_time = time.time() - start_time
        logger.info(f"请求完成: 问题长度={len(user_question)}, 总时间={total_time:.2f}s")
        
        return jsonify(response_data)
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"聊天接口异常: {e}, 耗时 {total_time:.2f}s")
        
        return jsonify({
            "error": "系统异常",
            "message": "请求处理失败",
            "answer": "抱歉，AI张老师暂时无法回答。请稍后再试！",
            "processing_time": total_time
        }), 500


@app.route("/health", methods=["GET"])
def health_check():
    """健康检查接口"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "fast-1.0",
        "config": {
            "max_response_time": MAX_RESPONSE_TIME,
            "rag_timeout": RAG_TIMEOUT,
            "llm_timeout": LLM_TIMEOUT,
            "cache_ttl": CACHE_TTL
        },
        "performance": monitor.get_summary()
    }
    return jsonify(health_status)


@app.route("/clear_cache", methods=["POST"])
def clear_cache_endpoint():
    """清理缓存接口"""
    try:
        prefix = request.json.get("prefix", None) if request.is_json else None
        result = clear_cache(prefix)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        logger.error(f"清理缓存失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/test_speed", methods=["POST"])
def test_speed():
    """速度测试接口"""
    start_time = time.time()
    
    try:
        data = request.get_json()
        test_question = data.get("question", "测试速度")
        
        # 测试RAG速度
        rag_start = time.time()
        rag_result = fast_rag_search(test_question)
        rag_time = time.time() - rag_start
        
        # 测试LLM速度
        llm_start = time.time()
        llm_result = fast_llm_generate(test_question, rag_result, [])
        llm_time = time.time() - llm_start
        
        total_time = time.time() - start_time
        
        return jsonify({
            "question": test_question,
            "rag_time": rag_time,
            "llm_time": llm_time,
            "total_time": total_time,
            "rag_result_length": len(rag_result),
            "llm_result_length": len(llm_result),
            "within_limit": total_time <= MAX_RESPONSE_TIME
        })
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"速度测试异常: {e}")
        
        return jsonify({
            "error": str(e),
            "total_time": total_time,
            "within_limit": total_time <= MAX_RESPONSE_TIME
        }), 500


@app.route("/", methods=["GET"])
def index():
    """主页面"""
    return render_template("index.html")


@app.route("/performance", methods=["GET"])
def performance_stats():
    """性能统计接口"""
    stats = {
        "timestamp": time.time(),
        "config": {
            "max_response_time": MAX_RESPONSE_TIME,
            "rag_timeout": RAG_TIMEOUT,
            "llm_timeout": LLM_TIMEOUT
        },
        "cache_stats": optimizer.get_stats() if hasattr(optimizer, 'get_stats') else {},
        "api_performance": monitor.get_summary()
    }
    return jsonify(stats)


if __name__ == "__main__":
    logger.info("启动快速版AI张老师服务...")
    logger.info(f"性能配置: RAG超时={RAG_TIMEOUT}s, LLM超时={LLM_TIMEOUT}s, 最大响应={MAX_RESPONSE_TIME}s")
    
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)