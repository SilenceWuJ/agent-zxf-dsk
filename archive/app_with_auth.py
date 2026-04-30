#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI张老师·数字分身 - 带登录认证版本
"""

import os
import time
import uuid
import json
import base64
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_login import login_required, current_user, logout_user
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入自定义模块
from promot.promot import promot_z
from services.rag_service import search_knowledge
from services.llm_service_improved import ask_llm
from services.llm_service_jiao import ask_llm_j
from services.tts_service import text_to_speech
from services.session_service import get_session, save_session
from services.filter_service import is_related_question
from services.app_service import call_application, call_application_with_context
from utils.cache_improved import get_cache, set_cache
from utils.performance import PerformanceMonitor
from utils.logger import setup_logger

# 导入数据库和认证模块
from models import db, init_db
from auth import init_auth, authenticate_user, register_user, create_user_session, get_user_session, save_chat_message, get_chat_history, logout_user_session, get_current_user_info

# 初始化应用
app = Flask(__name__)

# 配置Flask应用
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# 初始化数据库和认证
init_db(app)
login_manager = init_auth(app)

# 设置日志
logger = setup_logger()
performance_monitor = PerformanceMonitor()

# 线程池执行器
executor = ThreadPoolExecutor(max_workers=4)

# ==================== 工具函数 ====================

def optimized_search_knowledge(question: str) -> str:
    """优化版知识检索"""
    cache_key = f"search_{question[:50]}"
    cached = get_cache(cache_key)
    if cached:
        return cached if cached is not None else ""
    
    result = search_knowledge(question)
    # Ensure result is not None
    safe_result = result if result is not None else ""
    set_cache(cache_key, safe_result, expire=3600)
    return safe_result

def optimized_search_knowledge_j(question: str) -> str:
    """优化版知识检索（教育版）"""
    cache_key = f"search_j_{question[:50]}"
    cached = get_cache(cache_key)
    if cached:
        return cached if cached is not None else ""
    
    result = search_knowledge(question)
    # Ensure result is not None
    safe_result = result if result is not None else ""
    set_cache(cache_key, safe_result, expire=3600)
    return safe_result

def optimized_ask_llm(question: str, context: str, history: list) -> str:
    """优化版LLM调用"""
    # Handle None context
    safe_context = context if context is not None else ""
    cache_key = f"llm_{hash(question + safe_context + str(history))}"
    cached = get_cache(cache_key)
    if cached:
        return cached
    
    result = ask_llm(question, context, history)
    set_cache(cache_key, result, expire=1800)
    return result

def optimized_ask_llm_j(question: str, context: str, history: list) -> str:
    """优化版LLM调用（教育版）"""
    # Handle None context
    safe_context = context if context is not None else ""
    cache_key = f"llm_j_{hash(question + safe_context + str(history))}"
    cached = get_cache(cache_key)
    if cached:
        return cached
    
    result = ask_llm_j(question, context, history)
    set_cache(cache_key, result, expire=1800)
    return result

def optimized_text_to_speech(text: str) -> bytes:
    """优化版文本转语音"""
    cache_key = f"tts_{hash(text)}"
    cached = get_cache(cache_key)
    if cached:
        return cached
    
    result = text_to_speech(text)
    set_cache(cache_key, result, expire=86400)
    return result

def parallel_api_calls(question: str, need_audio: bool = True) -> dict:
    """并行API调用"""
    start_time = time.time()
    results = {
        "rag_result": "",
        "llm_result": "",
        "tts_result": None,
        "errors": []
    }

    request_id = str(uuid.uuid4())
    
    try:
        # 并行执行搜索和LLM调用
        with ThreadPoolExecutor(max_workers=2) as executor:
            # 提交搜索任务
            # rag_future = executor.submit(optimized_search_knowledge, question)
            search_future = executor.submit(optimized_search_knowledge, question)

            # 等待结果
            try:
                results["rag_result"] = search_future.result()
            except TimeoutError:
                logger.error("RAG任务超时")
                results["errors"].append("RAG超时")
            except Exception as e:
                logger.error(f"RAG任务异常: {e}", exc_info=True)
                results["errors"].append(f"RAG异常: {e}")

            
            # 提交LLM任务（依赖搜索结果）
            def llm_task():
                context = search_future.result()
                return optimized_ask_llm(question, context, [])
            
            llm_future = executor.submit(llm_task)
            
            # 等待所有任务完成
            search_result = search_future.result()
            llm_result = llm_future.result()
        
        # 检查LLM结果是否有效
        if not llm_result or not isinstance(llm_result, str):
            llm_result = "抱歉，我无法回答这个问题。请尝试问一个关于高考志愿、考研选择或职业规划的问题。"
        
        # 生成音频（如果需要）
        audio_data = None
        audio_format = None
        if need_audio:
            audio_data = optimized_text_to_speech(llm_result)
            audio_format = "mp3"
        
        duration = time.time() - start_time
        
        return {
            "success": True,
            "request_id": request_id,
            "output": {
                "text": llm_result,
                "audio_base64": base64.b64encode(audio_data).decode('utf-8') if audio_data else None,
                "audio_format": audio_format
            },
            "duration": duration,
            "cached": False
        }
        
    except Exception as e:
        logger.error(f"并行API调用失败: {e}")
        return {
            "success": False,
            "request_id": request_id,
            "error": str(e),
            "duration": time.time() - start_time
        }

def parallel_api_calls_j(question: str, need_audio: bool = True) -> dict:
    """并行API调用（教育版）"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # 并行执行搜索和LLM调用
        with ThreadPoolExecutor(max_workers=2) as executor:
            # 提交搜索任务
            search_future = executor.submit(optimized_search_knowledge_j, question)
            
            # 提交LLM任务（依赖搜索结果）
            def llm_task():
                context = search_future.result()
                return optimized_ask_llm_j(question, context, [])
            
            llm_future = executor.submit(llm_task)
            
            # 等待所有任务完成
            search_result = search_future.result()
            llm_result = llm_future.result()
        
        # 检查LLM结果是否有效
        if not llm_result or not isinstance(llm_result, str):
            llm_result = "抱歉，我无法回答这个问题。"
        
        # 生成音频（如果需要）
        audio_data = None
        audio_format = None
        if need_audio:
            audio_data = optimized_text_to_speech(llm_result)
            audio_format = "mp3"
        
        duration = time.time() - start_time
        
        return {
            "success": True,
            "request_id": request_id,
            "output": {
                "text": llm_result,
                "audio_base64": base64.b64encode(audio_data).decode('utf-8') if audio_data else None,
                "audio_format": audio_format
            },
            "duration": duration,
            "cached": False
        }
        
    except Exception as e:
        logger.error(f"并行API调用（教育版）失败: {e}")
        return {
            "success": False,
            "request_id": request_id,
            "error": str(e),
            "duration": time.time() - start_time
        }

# ==================== 路由定义 ====================

@app.route("/")
def home():
    """首页 - 重定向到登录页面"""
    return redirect(url_for('login'))

@app.route("/main")
@login_required
def main():
    """主页面（需要登录）"""
    return render_template("home.html")

@app.route("/login", methods=["GET"])
def login():
    """登录页面"""
    if current_user.is_authenticated:
        return redirect(url_for('main'))
    return render_template("login.html")

@app.route("/register", methods=["GET"])
def register():
    """注册页面"""
    if current_user.is_authenticated:
        return redirect(url_for('main'))
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    """退出登录"""
    # 获取当前会话ID
    session_id = request.headers.get('X-Session-ID') or request.args.get('session_id')
    if session_id:
        logout_user_session(session_id)
    
    # 退出登录
    logout_user()
    
    return redirect(url_for('login'))

# ==================== API路由 ====================

@app.route("/api/login", methods=["POST"])
def api_login():
    """API登录"""
    data = request.json
    if not data:
        return jsonify({"success": False, "message": "请求数据不能为空"}), 400
    
    username = data.get("username", "").strip()
    password = data.get("password", "")
    remember = data.get("remember", False)
    
    if not username or not password:
        return jsonify({"success": False, "message": "用户名和密码不能为空"}), 400
    
    result = authenticate_user(username, password, remember)
    
    if result["success"]:
        return jsonify(result), 200
    else:
        return jsonify(result), 401

@app.route("/api/register", methods=["POST"])
def api_register():
    """API注册"""
    data = request.json
    if not data:
        return jsonify({"success": False, "message": "请求数据不能为空"}), 400
    
    username = data.get("username", "").strip()
    password = data.get("password", "")
    email = data.get("email", "").strip() or None
    full_name = data.get("full_name", "").strip() or None
    
    if not username or not password:
        return jsonify({"success": False, "message": "用户名和密码不能为空"}), 400
    
    if len(username) < 3 or len(username) > 20:
        return jsonify({"success": False, "message": "用户名长度应为3-20个字符", "field": "username"}), 400
    
    if len(password) < 6:
        return jsonify({"success": False, "message": "密码长度至少为6个字符", "field": "password"}), 400
    
    result = register_user(username, password, email, full_name)
    
    if result["success"]:
        return jsonify(result), 201
    else:
        return jsonify(result), 400

@app.route("/api/user/info", methods=["GET"])
@login_required
def api_user_info():
    """获取用户信息"""
    user_info = get_current_user_info()
    if user_info:
        return jsonify({"success": True, "user": user_info}), 200
    else:
        return jsonify({"success": False, "message": "用户未登录"}), 401

@app.route("/api/chat/history", methods=["GET"])
@login_required
def api_chat_history():
    """获取聊天历史"""
    session_id = request.args.get("session_id")
    limit = int(request.args.get("limit", 50))
    
    history = get_chat_history(current_user.id, session_id, limit)
    
    history_list = []
    for item in reversed(history):  # 按时间正序返回
        history_list.append({
            "id": item.id,
            "message_type": item.message_type,
            "content": item.content,
            "context": item.context,
            "response_time": item.response_time,
            "created_at": item.created_at.isoformat() if item.created_at else None
        })
    
    return jsonify({
        "success": True,
        "history": history_list,
        "count": len(history_list)
    }), 200

# ==================== 原有聊天路由（需要登录） ====================

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    """标准聊天接口（需要登录）"""
    start_time = time.time()
    
    try:
        data = request.json
        if not data:
            return jsonify({"error": "请求数据不能为空"}), 400
        
        question = data.get("question", "").strip()
        if not question:
            return jsonify({
                "error": "请输入问题",
                "answer": "请告诉我你想了解什么专业或院校信息？"
            }), 400
        
        need_audio = data.get("need_audio", True)
        session_id = data.get("session_id")
        
        logger.info(f"聊天请求: {question[:50]}...")
        
        # 调用API
        result = parallel_api_calls(question, need_audio)
        
        # 保存聊天记录到数据库
        if result.get("success") and current_user.is_authenticated:
            # 使用提供的session_id或生成新的
            user_session_id = session_id or str(uuid.uuid4())
            
            # 保存用户消息
            save_chat_message(
                user_id=current_user.id,
                session_id=user_session_id,
                message_type="user",
                content=question,
                response_time=None
            )
            
            # 保存助手回复
            save_chat_message(
                user_id=current_user.id,
                session_id=user_session_id,
                message_type="assistant",
                content=result.get("output", {}).get("text", ""),
                response_time=result.get("duration", 0)
            )
        
        # 构建响应
        response_data = {
            "question": question,
            "answer": result.get("output", {}).get("text", "") if result.get("success") else "",
            "audio_base64": result.get("output", {}).get("audio_base64"),
            "audio_format": result.get("output", {}).get("audio_format"),
            "success": result.get("success", False),
            "request_id": result.get("request_id", ""),
            "duration": result.get("duration", 0),
            "cached": result.get("cached", False),
            "processing_time": time.time() - start_time
        }
        
        if not result.get("success"):
            response_data["error"] = result.get("error", "未知错误")
        
        logger.info(f"聊天完成，耗时: {response_data['processing_time']:.2f}秒")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"聊天异常: {e}")
        return jsonify({
            "error": str(e),
            "processing_time": time.time() - start_time,
            "success": False
        }), 500

@app.route("/app/chat", methods=["POST"])
@login_required
def app_chat():
    """应用ID调用接口（需要登录）"""
    start_time = time.time()
    
    try:
        data = request.json
        if not data:
            return jsonify({"error": "请求数据不能为空"}), 400
        
        question = data.get("question", "").strip()
        if not question:
            return jsonify({"error": "问题不能为空"}), 400
        
        context = data.get("context", "")
        use_cache = data.get("use_cache", True)
        session_id = data.get("session_id")
        
        logger.info(f"应用ID调用请求: {question[:50]}...")
        
        # 获取历史（如果有session_id）
        history = []
        if session_id:
            session_data = get_session(session_id)
            if session_data:
                history = session_data.get("history", [])
        
        # 调用应用ID服务
        result = call_application_with_context(
            prompt=question,
            context=context,
            history=history,
            use_cache=use_cache
        )
        
        # 保存聊天记录到数据库
        if result.get("success") and current_user.is_authenticated:
            # 使用提供的session_id或生成新的
            user_session_id = session_id or str(uuid.uuid4())
            
            # 保存用户消息
            save_chat_message(
                user_id=current_user.id,
                session_id=user_session_id,
                message_type="user",
                content=question,
                context=context,
                response_time=None
            )
            
            # 保存助手回复
            save_chat_message(
                user_id=current_user.id,
                session_id=user_session_id,
                message_type="assistant",
                content=result.get("output", {}).get("text", ""),
                response_time=result.get("duration", 0)
            )
        
        # 构建响应
        response_data = {
            "question": question,
            "answer": result.get("output", {}).get("text", "") if result.get("success") else "",
            "success": result.get("success", False),
            "request_id": result.get("request_id", ""),
            "duration": result.get("duration", 0),
            "cached": result.get("cached", False),
            "processing_time": time.time() - start_time
        }
        
        if not result.get("success"):
            response_data["error"] = result.get("error", "未知错误")
        
        # 如果有session_id，保存历史
        if session_id and result.get("success"):
            new_history = history + [
                {"role": "user", "content": question},
                {"role": "assistant", "content": response_data["answer"]}
            ]
            save_session(session_id, {"history": new_history})
        
        logger.info(f"应用ID调用完成，耗时: {response_data['processing_time']:.2f}秒")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"应用ID调用异常: {e}")
        return jsonify({
            "error": str(e),
            "processing_time": time.time() - start_time,
            "success": False
        }), 500

# ==================== 其他路由 ====================

@app.route("/health", methods=["GET"])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

@app.route("/clear_cache", methods=["POST"])
def clear_cache():
    """清空缓存"""
    # 这里需要实现清空缓存的逻辑
    return jsonify({"success": True, "message": "缓存已清空"})

@app.route("/standard", methods=["GET"])
@login_required
def standard_index():
    """标准版主页面（需要登录）"""
    return render_template("index.html")

@app.route("/app", methods=["GET"])
@login_required
def app_index():
    """应用版主页面（需要登录）"""
    return render_template("app_index.html", hide_main_js=True)

@app.route("/app/test", methods=["GET"])
def app_test():
    """应用ID测试接口"""
    try:
        result = call_application("你是谁？")
        return jsonify({
            "success": result.get("success", False),
            "answer": result.get("output", {}).get("text", "") if result.get("success") else "",
            "error": result.get("error") if not result.get("success") else None
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/pedu", methods=["GET"])
@login_required
def pedu_index():
    """教育版主页面（需要登录）"""
    return render_template("pedu_index.html")

@app.route("/pedu/chat", methods=["POST"])
@login_required
def pedu_chat():
    """教育版聊天接口（需要登录）"""
    start_time = time.time()
    
    try:
        data = request.json
        if not data:
            return jsonify({"error": "请求数据不能为空"}), 400
        
        question = data.get("question", "").strip()
        if not question:
            return jsonify({"error": "问题不能为空"}), 400
        
        need_audio = data.get("need_audio", True)
        session_id = data.get("session_id")
        
        logger.info(f"教育版聊天请求: {question[:50]}...")
        
        # 调用教育版API
        result = parallel_api_calls_j(question, need_audio)
        
        # 保存聊天记录到数据库
        if result.get("success") and current_user.is_authenticated:
            # 使用提供的session_id或生成新的
            user_session_id = session_id or str(uuid.uuid4())
            
            # 保存用户消息
            save_chat_message(
                user_id=current_user.id,
                session_id=user_session_id,
                message_type="user",
                content=question,
                response_time=None
            )
            
            # 保存助手回复
            save_chat_message(
                user_id=current_user.id,
                session_id=user_session_id,
                message_type="assistant",
                content=result.get("output", {}).get("text", ""),
                response_time=result.get("duration", 0)
            )
        
        # 构建响应
        response_data = {
            "question": question,
            "answer": result.get("output", {}).get("text", "") if result.get("success") else "",
            "audio_base64": result.get("output", {}).get("audio_base64"),
            "audio_format": result.get("output", {}).get("audio_format"),
            "success": result.get("success", False),
            "request_id": result.get("request_id", ""),
            "duration": result.get("duration", 0),
            "cached": result.get("cached", False),
            "processing_time": time.time() - start_time
        }
        
        if not result.get("success"):
            response_data["error"] = result.get("error", "未知错误")
        
        logger.info(f"教育版聊天完成，耗时: {response_data['processing_time']:.2f}秒")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"教育版聊天异常: {e}")
        return jsonify({
            "error": str(e),
            "processing_time": time.time() - start_time,
            "success": False
        }), 500

@app.route("/pedu/test", methods=["GET"])
def pedu_test():
    """教育版测试接口"""
    try:
        question = "介绍一下你自己"
        result = parallel_api_calls_j(question, need_audio=False)
        
        return jsonify({
            "success": result.get("success", False),
            "question": question,
            "answer": result.get("output", {}).get("text", "") if result.get("success") else "",
            "error": result.get("error") if not result.get("success") else None
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/performance", methods=["GET"])
def performance_stats():
    """性能统计"""
    stats = performance_monitor.get_stats()
    return jsonify(stats)

@app.route('/favicon.ico')
def favicon():
    """处理favicon请求"""
    return app.send_static_file('images/favicon.ico')

# ==================== 主程序 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("AI张老师·数字分身 - 带登录认证版本")
    print("=" * 50)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"数据库: SQLite (app.db)")
    print(f"测试用户: testuser / test123")
    print(f"测试管理员: admin / admin123")
    print("=" * 50)
    
    # 启动Flask应用
    app.run(host="0.0.0.0", port=5002, debug=True)