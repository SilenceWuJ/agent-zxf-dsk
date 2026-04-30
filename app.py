#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
优化版本的应用入口
主要优化点：
1. 并行化API调用
2. 添加缓存机制
3. 优化错误处理
4. 减少不必要的动作描述
"""

import os
import time
import uuid
import json
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify, render_template, Response, redirect, url_for
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
import requests
from dotenv import load_dotenv
from promot.promot import promot_z
from services.rag_service import search_knowledge, search_knowledge_j
from services.llm_service_improved import ask_llm
from services.llm_service_jiao import ask_llm_j
from services.tts_service import text_to_speech
from services.session_service import get_session, save_session
from services.filter_service import is_related_question
from services.app_service import call_application, call_application_with_context, call_pedu_application
from utils.cache_improved import get_cache, set_cache
from utils.performance import monitor, optimizer, time_it
from utils.logger import logger

# 认证与数据库
from models import db, init_db
from auth import init_auth, authenticate_user, register_user, login_by_phone, send_verification_code, \
    get_current_user_info, create_user_session, save_chat_message, get_chat_history, logout_user_session, \
    get_user_session

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# ==================== 认证配置 ====================
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 初始化数据库和认证
init_db(app)
login_manager = init_auth(app)

# ==================== 配置区域 ====================
# DeepSeek API - 从环境变量读取
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# 阿里云百炼知识库配置
ALIYUN_API_KEY = os.getenv("ALIYUN_API_KEY")

ALIYUN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID", "7lef75e879")

KNOWLEDGE_BASE_ID_J = os.getenv("KNOWLEDGE_BASE_ID_J")

ALIYUN_APP_ID = os.getenv("ALIYUN_APP_ID")
ALIYUN_APP_ID_J = os.getenv("ALIYUN_APP_ID_J")

# 语音合成配置
TTS_VOICE = "longanyang"
TTS_MODEL = "cosyvoice-v3-flash"
TTS_FORMAT = "mp3"

# 系统提示词 - 优化版本，去掉动作描述
SYSTEM_PROMPT = promot_z

# ==================== 优化函数 ====================

@time_it
def optimized_search_knowledge(question: str) -> str:
    """优化的知识库搜索函数"""

    cache_key = f"rag:{question[:50]}"

    # 尝试读取缓存（如果启用）
    try:
        cached = get_cache(cache_key)
        if cached:
            return cached
    except Exception as cache_err:
        logger.warning(f"读取RAG缓存失败: {cache_err}")

    monitor.start_timer("rag_search")
    try:
        result = search_knowledge(question)
        monitor.end_timer("rag_search")

        # 缓存结果（非关键操作，不应影响主流程）
        if result:
            try:
                set_cache(cache_key, result, expire=30)
            except Exception as cache_err:
                logger.warning(f"写入RAG缓存失败: {cache_err}")

        return result
    except Exception as e:
        monitor.end_timer("rag_search")
        logger.error(f"RAG搜索失败: {e}", exc_info=True)  # 打印堆栈
        return ""

@time_it
def optimized_search_knowledge_j(question: str) -> str:
    """优化的知识库搜索函数"""

    cache_key = f"rag:{question[:50]}"

    # 尝试读取缓存（如果启用）
    try:
        cached = get_cache(cache_key)
        if cached:
            return cached
    except Exception as cache_err:
        logger.warning(f"读取RAG缓存失败: {cache_err}")

    monitor.start_timer("rag_search")
    try:
        result = search_knowledge_j(question)
        monitor.end_timer("rag_search")

        # 缓存结果（非关键操作，不应影响主流程）
        if result:
            try:
                set_cache(cache_key, result, expire=30)
            except Exception as cache_err:
                logger.warning(f"写入RAG缓存失败: {cache_err}")

        return result
    except Exception as e:
        monitor.end_timer("rag_search")
        logger.error(f"RAG搜索失败: {e}", exc_info=True)  # 打印堆栈
        return ""


@time_it
def optimized_ask_llm(question: str, context: str, history: list) -> str:
    """优化的LLM调用函数"""
    cache_key = f"llm:{question[:50]}:{hash(context) if context else 'no_context'}"
    
    # 尝试从缓存获取
    cached_result = get_cache(cache_key)
    if cached_result:
        logger.info(f"LLM缓存命中: {question[:30]}...")
        return cached_result
    
    # 调用LLM
    monitor.start_timer("llm_generation")
    try:
        # 如果上下文为空，使用简化的提示词
        if not context:
            prompt = f"问题：{question}\n\n请用AI张老师的风格回答这个问题。"
        else:
            prompt = f"已知信息：\n{context}\n\n问题：{question}\n\n请基于以上已知信息，用AI张老师的风格回答用户问题。"
        
        # 这里可以添加更智能的提示词优化
        result = ask_llm(question, context, history)
        monitor.end_timer("llm_generation")
        
        # 缓存结果
        if result:
            set_cache(cache_key, result, expire=600)  # 缓存10分钟
        
        return result
    except Exception as e:
        monitor.end_timer("llm_generation")
        logger.error(f"LLM生成失败: {e}")
        return "抱歉，AI张老师暂时无法回答这个问题。"


@time_it
def optimized_ask_llm_j(question: str, context: str, history: list) -> str:
    """优化的LLM调用函数"""
    cache_key = f"llm:{question[:50]}:{hash(context) if context else 'no_context'}"

    # 尝试从缓存获取
    cached_result = get_cache(cache_key)
    if cached_result:
        logger.info(f"LLM缓存命中: {question[:30]}...")
        return cached_result

    # 调用LLM
    monitor.start_timer("llm_generation")
    try:
        # 如果上下文为空，使用简化的提示词
        if not context:
            prompt = f"问题：{question}\n\n请用开国领袖教员的风格回答这个问题。"
        else:
            prompt = f"已知信息：\n{context}\n\n问题：{question}\n\n请基于以上已知信息，用教员的风格回答用户问题。"

        # 这里可以添加更智能的提示词优化
        result = ask_llm_j(question, context, history)
        monitor.end_timer("llm_generation")

        # 缓存结果
        if result:
            set_cache(cache_key, result, expire=600)  # 缓存10分钟

        return result
    except Exception as e:
        monitor.end_timer("llm_generation")
        logger.error(f"LLM生成失败: {e}")
        return "抱歉，无法回答该问题。"


@time_it
def optimized_text_to_speech(text: str) -> bytes:
    """优化的TTS合成函数"""
    if not text or len(text) < 10:
        return None
    
    cache_key = f"tts:{hash(text)}"
    
    # 尝试从缓存获取
    cached_result = get_cache(cache_key)
    if cached_result:
        logger.info(f"TTS缓存命中: 文本长度{len(text)}")
        return cached_result
    
    # 执行TTS合成
    monitor.start_timer("tts_synthesis")
    try:
        result = text_to_speech(text)
        monitor.end_timer("tts_synthesis")
        
        # 缓存结果
        if result:
            set_cache(cache_key, result, expire=1800)  # 缓存30分钟
        
        return result
    except Exception as e:
        monitor.end_timer("tts_synthesis")
        logger.error(f"TTS合成失败: {e}")
        return None


def parallel_api_calls(question: str, session_id: str = None, need_audio: bool = True) -> dict:
    """
    并行执行API调用

    优化策略：
    1. RAG和LLM可以并行执行（如果LLM不需要RAG结果）
    2. TTS可以在LLM生成后立即开始
    """
    results = {
        "rag_result": "",
        "llm_result": "",
        "tts_result": None,
        "errors": [],
        "session_id": session_id
    }

    # 第一阶段：并行执行RAG和获取会话历史
    with ThreadPoolExecutor(max_workers=2) as executor:
        # 提交RAG任务
        rag_future = executor.submit(optimized_search_knowledge, question)

        # 使用传入的session_id或生成新的
        if not session_id:
            session_id = str(uuid.uuid4())
            results["session_id"] = session_id
        history_future = executor.submit(get_session, session_id)
        
        # 等待结果
        try:
            results["rag_result"] = rag_future.result()
        except TimeoutError:
            logger.error("RAG任务超时")
            results["errors"].append("RAG超时")
        except Exception as e:
            logger.error(f"RAG任务异常: {e}", exc_info=True)
            results["errors"].append(f"RAG异常: {e}")

        
        try:
            history = history_future.result(timeout=10)
        except Exception as e:
            logger.error(f"获取会话历史失败: {e}")
            history = []
    
    # 第二阶段：执行LLM生成
    try:
        results["llm_result"] = optimized_ask_llm(question, results["rag_result"], history)
        
        # 更新会话历史
        if history is not None:
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": results["llm_result"]})
            save_session(session_id, history)
    except Exception as e:
        logger.error(f"LLM生成失败: {e}")
        results["errors"].append(f"LLM失败: {e}")
        results["llm_result"] = "抱歉，AI张老师暂时无法回答这个问题。"
    
    # # 第三阶段：如果需要音频，执行TTS合成
    # if need_audio and results["llm_result"]:
    #     try:
    #         results["tts_result"] = optimized_text_to_speech(results["llm_result"])
    #     except Exception as e:
    #         logger.error(f"TTS合成失败: {e}")
    #         results["errors"].append(f"TTS失败: {e}")
    
    return results


def parallel_api_calls_j(question: str, session_id: str = None, need_audio: bool = True) -> dict:
    """
    并行执行API调用

    优化策略：
    1. RAG和LLM可以并行执行（如果LLM不需要RAG结果）
    2. TTS可以在LLM生成后立即开始
    """
    results = {
        "rag_result": "",
        "llm_result": "",
        "tts_result": None,
        "errors": [],
        "session_id": session_id
    }

    # 第一阶段：并行执行RAG和获取会话历史
    with ThreadPoolExecutor(max_workers=2) as executor:
        # 提交RAG任务
        rag_future = executor.submit(optimized_search_knowledge_j, question)

        # 使用传入的session_id或生成新的
        if not session_id:
            session_id = str(uuid.uuid4())
            results["session_id"] = session_id
        history_future = executor.submit(get_session, session_id)

        # 等待结果
        try:
            results["rag_result"] = rag_future.result()
        except TimeoutError:
            logger.error("RAG任务超时")
            results["errors"].append("RAG超时")
        except Exception as e:
            logger.error(f"RAG任务异常: {e}", exc_info=True)
            results["errors"].append(f"RAG异常: {e}")

        try:
            history = history_future.result(timeout=10)
        except Exception as e:
            logger.error(f"获取会话历史失败: {e}")
            history = []

    # 第二阶段：执行LLM生成
    try:
        results["llm_result"] = optimized_ask_llm_j(question, results["rag_result"], history)

        # 更新会话历史
        if history is not None:
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": results["llm_result"]})
            save_session(session_id, history)
    except Exception as e:
        logger.error(f"LLM生成失败: {e}")
        results["errors"].append(f"LLM失败: {e}")
        results["llm_result"] = "抱歉，无法回答这个问题。"

    # # 第三阶段：如果需要音频，执行TTS合成
    # if need_audio and results["llm_result"]:
    #     try:
    #         results["tts_result"] = optimized_text_to_speech(results["llm_result"])
    #     except Exception as e:
    #         logger.error(f"TTS合成失败: {e}")
    #         results["errors"].append(f"TTS失败: {e}")

    return results


# ==================== 路由函数 ====================

@app.route("/chat", methods=["POST"])
def chat():
    """优化的主对话接口"""
    start_time = time.time()

    try:
        data = request.get_json()
        user_question = data.get("question", "").strip()
        need_audio = data.get("need_audio", True)
        session_id = data.get("session_id")

        if not user_question:
            return jsonify({
                "error": "请输入问题",
                "answer": "请告诉我你想了解什么专业或院校信息？"
            }), 400

        # 检查问题是否相关（可选）
        # if not is_related_question(user_question):
        #     return jsonify({
        #         "answer": "这个问题超出了我的专业范围。我是专门帮助大家解决高考志愿、考研选择和职业规划问题的。你有什么关于专业选择或就业方面的问题吗？",
        #         "filtered": True
        #     })

        # 如果已登录，获取或创建用户会话
        db_session_id = None
        if current_user.is_authenticated:
            if not session_id:
                # 创建新的用户会话
                user_session = create_user_session(current_user.id, request)
                session_id = user_session.session_id
                db_session_id = session_id
            else:
                # 检查session_id是否属于当前用户
                user_session = get_user_session(session_id)
                if user_session and user_session.user_id == current_user.id:
                    db_session_id = session_id
                else:
                    # session无效，创建新的
                    user_session = create_user_session(current_user.id, request)
                    session_id = user_session.session_id
                    db_session_id = session_id

        # 检查缓存
        cache_key = f"chat:{user_question}"
        cached_response = get_cache(cache_key)
        if cached_response:
            logger.info(f"完整响应缓存命中: {user_question[:30]}...")
            return jsonify(cached_response)

        # 执行并行API调用，传入session_id
        logger.info(f"开始处理问题: {user_question[:50]}...")
        api_results = parallel_api_calls(user_question, session_id, need_audio)

        # 构建响应
        response_data = {
            "answer": api_results["llm_result"],
            "session_id": api_results.get("session_id", session_id),
            "processing_time": time.time() - start_time,
            "cached": False
        }

        # 添加音频数据
        if need_audio and api_results["tts_result"]:
            response_data["audio_base64"] = base64.b64encode(api_results["tts_result"]).decode("utf-8")
            response_data["audio_format"] = TTS_FORMAT

        # 添加错误信息（如果有）
        if api_results["errors"]:
            response_data["warnings"] = api_results["errors"]

        # 缓存响应
        set_cache(cache_key, response_data, expire=300)

        # 保存聊天记录到数据库（如果已登录）
        if current_user.is_authenticated and db_session_id:
            try:
                save_chat_message(
                    user_id=current_user.id,
                    session_id=db_session_id,
                    message_type="user",
                    content=user_question,
                    response_time=None
                )
                save_chat_message(
                    user_id=current_user.id,
                    session_id=db_session_id,
                    message_type="assistant",
                    content=response_data.get("answer", ""),
                    response_time=response_data.get("processing_time", 0)
                )
                logger.info(f"保存聊天记录成功: user_id={current_user.id}, session_id={db_session_id}")
            except Exception as db_err:
                logger.error(f"保存聊天记录失败: {db_err}", exc_info=True)
        
        # 记录性能指标
        total_time = time.time() - start_time
        logger.info(f"请求处理完成: 问题长度={len(user_question)}, 总时间={total_time:.2f}s")
        
        # 如果处理时间过长，记录警告
        if total_time > 10.0:
            logger.warning(f"请求处理时间过长: {total_time:.2f}s")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"聊天接口异常: {e}")
        return jsonify({
            "error": "内部服务器错误",
            "message": str(e),
            "answer": "抱歉，AI张老师暂时无法回答。请稍后再试！"
        }), 500


@app.route("/health", methods=["GET"])
def health_check():
    """健康检查接口"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "deepseek": bool(DEEPSEEK_API_KEY),
            "aliyun": bool(ALIYUN_API_KEY),
            "cache": True,
            "logger": True
        },
        "performance": monitor.get_summary()
    }
    return jsonify(health_status)


@app.route("/clear_cache", methods=["POST"])
def clear_cache():
    """清理缓存接口"""
    try:
        prefix = request.json.get("prefix", None) if request.is_json else None
        optimizer.clear_cache(prefix)
        return jsonify({"success": True, "message": "缓存已清理"})
    except Exception as e:
        logger.error(f"清理缓存失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/", methods=["GET"])
def home():
    """主页选择页面 - 未登录跳转登录页"""
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template("home.html")

@app.route("/home", methods=["GET"])
@login_required
def home_page():
    """主页面（需登录）"""
    return render_template("home.html")


# ==================== 认证路由 ====================

@app.route("/login", methods=["GET"], endpoint='login')
def login_page():
    """登录页面"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return render_template("login.html")

@app.route("/register", methods=["GET"], endpoint='register')
def register_page():
    """注册页面"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    """退出登录"""
    session_id = request.args.get('session_id')
    if session_id:
        logout_user_session(session_id)
    logout_user()
    return redirect(url_for('login_page'))


# ==================== 认证 API ====================

@app.route("/api/login", methods=["POST"])
def api_login():
    """API: 密码登录"""
    data = request.json
    if not data:
        return jsonify({"success": False, "message": "请求数据不能为空"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"success": False, "message": "用户名和密码不能为空"}), 400

    result = authenticate_user(username, password)
    if result["success"]:
        return jsonify(result), 200
    return jsonify(result), 401

@app.route("/api/register", methods=["POST"])
def api_register():
    """API: 注册"""
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
        return jsonify({"success": False, "message": "用户名长度应为3-20个字符"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "message": "密码长度至少为6个字符"}), 400

    result = register_user(username, password, email, full_name)
    if result["success"]:
        return jsonify(result), 201
    return jsonify(result), 400

@app.route("/api/send-code", methods=["POST"])
def api_send_code():
    """API: 发送手机验证码"""
    data = request.json
    if not data:
        return jsonify({"success": False, "message": "请求数据不能为空"}), 400

    phone = data.get("phone", "").strip()
    if not phone:
        return jsonify({"success": False, "message": "手机号不能为空"}), 400
    if not phone.isdigit() or len(phone) != 11:
        return jsonify({"success": False, "message": "手机号格式不正确"}), 400

    result = send_verification_code(phone)
    if result["success"]:
        return jsonify(result), 200
    return jsonify(result), 429

@app.route("/api/phone-login", methods=["POST"])
def api_phone_login():
    """API: 手机验证码登录"""
    data = request.json
    if not data:
        return jsonify({"success": False, "message": "请求数据不能为空"}), 400

    phone = data.get("phone", "").strip()
    code = data.get("code", "").strip()

    if not phone or not code:
        return jsonify({"success": False, "message": "手机号和验证码不能为空"}), 400
    if not phone.isdigit() or len(phone) != 11:
        return jsonify({"success": False, "message": "手机号格式不正确"}), 400
    if not code.isdigit() or len(code) != 6:
        return jsonify({"success": False, "message": "验证码为6位数字"}), 400

    result = login_by_phone(phone, code)
    if result["success"]:
        return jsonify(result), 200
    return jsonify(result), 401

@app.route("/api/user/info", methods=["GET"])
@login_required
def api_user_info():
    """API: 获取当前用户信息"""
    user_info = get_current_user_info()
    if user_info:
        return jsonify({"success": True, "user": user_info}), 200
    return jsonify({"success": False, "message": "未登录"}), 401

@app.route("/cyborg", methods=["GET"])
@login_required
def cyborg_index():
    """赛博人·AI智能体选择页面"""
    return render_template("cyborg.html")

@app.route("/standard", methods=["GET"])
@login_required
def standard_index():
    """标准版主页面"""
    return render_template("index.html")

@app.route("/app", methods=["GET"])
@login_required
def app_index():
    """应用版主页面"""
    return render_template("app_index.html")

@app.route("/pedu", methods=["GET"])
@login_required
def pedu_index():
    """教育版主页面"""
    return render_template("pedu_index.html")


@app.route("/app/chat", methods=["POST"])
def app_chat():
    """应用ID调用接口"""
    start_time = time.time()

    try:
        # 获取请求数据
        data = request.json
        if not data:
            return jsonify({"error": "请求数据不能为空"}), 400

        question = data.get("question", "").strip()
        if not question:
            return jsonify({"error": "问题不能为空"}), 400

        # 可选参数
        context = data.get("context", "")
        use_cache = data.get("use_cache", True)
        session_id = data.get("session_id")

        # 如果已登录，获取或创建用户会话
        db_session_id = None
        if current_user.is_authenticated:
            if not session_id:
                # 创建新的用户会话
                user_session = create_user_session(current_user.id, request)
                session_id = user_session.session_id
                db_session_id = session_id
            else:
                # 检查session_id是否属于当前用户
                user_session = get_user_session(session_id)
                if user_session and user_session.user_id == current_user.id:
                    db_session_id = session_id
                else:
                    # session无效，创建新的
                    user_session = create_user_session(current_user.id, request)
                    session_id = user_session.session_id
                    db_session_id = session_id

        logger.info(f"应用ID调用请求: {question[:50]}...")

        # 如果有session_id，获取历史
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

        # 构建响应
        response_data = {
            "question": question,
            "answer": result.get("output", {}).get("text", "") if result.get("success") else "",
            "success": result.get("success", False),
            "request_id": result.get("request_id", ""),
            "duration": result.get("duration", 0),
            "cached": result.get("cached", False),
            "processing_time": time.time() - start_time,
            "session_id": session_id
        }

        # 如果有错误，添加错误信息
        if not result.get("success"):
            response_data["error"] = result.get("error", "未知错误")

        # 如果有session_id，保存历史
        if session_id and result.get("success"):
            # 添加当前对话到历史
            new_history = history + [
                {"role": "user", "content": question},
                {"role": "assistant", "content": response_data["answer"]}
            ]
            save_session(session_id, {"history": new_history})

        # 保存聊天记录到数据库（如果已登录）
        if current_user.is_authenticated and db_session_id and result.get("success"):
            try:
                save_chat_message(
                    user_id=current_user.id,
                    session_id=db_session_id,
                    message_type="user",
                    content=question,
                    response_time=None
                )
                save_chat_message(
                    user_id=current_user.id,
                    session_id=db_session_id,
                    message_type="assistant",
                    content=response_data.get("answer", ""),
                    response_time=response_data.get("duration", 0)
                )
                logger.info(f"保存应用聊天记录成功: user_id={current_user.id}, session_id={db_session_id}")
            except Exception as db_err:
                logger.error(f"保存聊天记录失败: {db_err}", exc_info=True)
        
        logger.info(f"应用ID调用完成，耗时: {response_data['processing_time']:.2f}秒")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"应用ID调用异常: {e}")
        return jsonify({
            "error": str(e),
            "processing_time": time.time() - start_time,
            "success": False
        }), 500


@app.route("/app/test", methods=["GET"])
def app_test():
    """应用ID测试接口"""
    try:
        # 简单测试调用
        result = call_application("你是谁？")
        
        return jsonify({
            "success": result.get("success", False),
            "output": result.get("output", {}).get("text", "") if result.get("success") else "",
            "error": result.get("error", "") if not result.get("success") else "",
            "app_id_configured": bool(os.getenv("ALIYUN_APP_ID")),
            "api_key_configured": bool(os.getenv("ALIYUN_API_KEY"))
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "app_id_configured": bool(os.getenv("ALIYUN_APP_ID")),
            "api_key_configured": bool(os.getenv("ALIYUN_API_KEY"))
        }), 500


@app.route("/pedu/chat", methods=["POST"])
def pedu_chat():
    """教员对话接口"""
    start_time = time.time()

    try:
        data = request.get_json()
        user_question = data.get("question", "").strip()
        need_audio = data.get("need_audio", True)
        session_id = data.get("session_id")

        if not user_question:
            return jsonify({
                "error": "请输入问题",
                "answer": "请告诉我你想了解什么？"
            }), 400

        # 如果已登录，获取或创建用户会话
        db_session_id = None
        if current_user.is_authenticated:
            if not session_id:
                # 创建新的用户会话
                user_session = create_user_session(current_user.id, request)
                session_id = user_session.session_id
                db_session_id = session_id
            else:
                # 检查session_id是否属于当前用户
                user_session = get_user_session(session_id)
                if user_session and user_session.user_id == current_user.id:
                    db_session_id = session_id
                else:
                    # session无效，创建新的
                    user_session = create_user_session(current_user.id, request)
                    session_id = user_session.session_id
                    db_session_id = session_id

        # 检查缓存
        cache_key = f"pedu:{user_question}"
        cached_response = get_cache(cache_key)
        if cached_response:
            logger.info(f"教员完整响应缓存命中: {user_question[:30]}...")
            return jsonify(cached_response)

        # 执行并行API调用，传入session_id
        logger.info(f"开始处理教员问题: {user_question[:50]}...")
        api_results = parallel_api_calls_j(user_question, session_id, need_audio)

        # 构建响应
        response_data = {
            "answer": api_results["llm_result"],
            "session_id": api_results.get("session_id", session_id),
            "processing_time": time.time() - start_time,
            "cached": False
        }

        # 添加音频数据
        if need_audio and api_results["tts_result"]:
            response_data["audio_base64"] = base64.b64encode(api_results["tts_result"]).decode("utf-8")
            response_data["audio_format"] = TTS_FORMAT

        # 添加错误信息（如果有）
        if api_results["errors"]:
            response_data["warnings"] = api_results["errors"]

        # 缓存响应
        set_cache(cache_key, response_data, expire=300)

        # 保存聊天记录到数据库（如果已登录）
        if current_user.is_authenticated and db_session_id:
            try:
                save_chat_message(
                    user_id=current_user.id,
                    session_id=db_session_id,
                    message_type="user",
                    content=user_question,
                    response_time=None
                )
                save_chat_message(
                    user_id=current_user.id,
                    session_id=db_session_id,
                    message_type="assistant",
                    content=response_data.get("answer", ""),
                    response_time=response_data.get("processing_time", 0)
                )
                logger.info(f"保存教员聊天记录成功: user_id={current_user.id}, session_id={db_session_id}")
            except Exception as db_err:
                logger.error(f"保存聊天记录失败: {db_err}", exc_info=True)

        # 记录性能指标
        total_time = time.time() - start_time
        logger.info(f"请求处理完成: 问题长度={len(user_question)}, 总时间={total_time:.2f}s")

        # 如果处理时间过长，记录警告
        if total_time > 10.0:
            logger.warning(f"请求处理时间过长: {total_time:.2f}s")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"聊天接口异常: {e}")
        return jsonify({
            "error": "内部服务器错误",
            "message": str(e),
            "answer": "抱歉，暂时无法回答。请稍后再试！"
        }), 500


#         # 获取请求数据
#         data = request.json
#         if not data:
#             return jsonify({"error": "请求数据不能为空"}), 400
#
#         question = data.get("question", "").strip()
#         if not question:
#             return jsonify({"error": "问题不能为空"}), 400
#
#         # 可选参数
#         context = data.get("context", "")
#         use_cache = data.get("use_cache", True)
#         session_id = data.get("session_id")
#
#         logger.info(f"教育版应用ID调用请求: {question[:50]}...")
#
#         # 如果有session_id，获取历史
#         history = []
#         if session_id:
#             print("sessionId_edu:",session_id)
#             session_data = get_session(session_id)
#             if session_data:
#                 history = session_data.get("history", [])
#
#         # 调用教育版应用ID服务
#         result = call_pedu_application(
#             prompt=question,
#             context=context,
#             history=history,
#             use_cache=use_cache
#         )
#
#         # 构建响应
#         response_data = {
#             "question": question,
#             "answer": result.get("output", {}).get("text", "") if result.get("success") else "",
#             "success": result.get("success", False),
#             "request_id": result.get("request_id", ""),
#             "duration": result.get("duration", 0),
#             "cached": result.get("cached", False),
#             "processing_time": time.time() - start_time,
#             "app_id": "fb610534bd5b4951ba9b1dc0bee1713b",
#             "knowledge_base_id": "jnulz2d020"
#         }
#
#         # 如果有错误，添加错误信息
#         if not result.get("success"):
#             response_data["error"] = result.get("error", "未知错误")
#
#         # 如果有session_id，保存历史
#         if session_id and result.get("success"):
#             # 添加当前对话到历史
#             new_history = history + [
#                 {"role": "user", "content": question},
#                 {"role": "assistant", "content": response_data["answer"]}
#             ]
#             save_session(session_id, {"history": new_history})
#
#         logger.info(f"教育版应用ID调用完成，耗时: {response_data['processing_time']:.2f}秒")
#         return jsonify(response_data)
#
#     except Exception as e:
#         logger.error(f"教育版应用ID调用异常: {e}")
#         return jsonify({
#             "error": str(e),
#             "processing_time": time.time() - start_time,
#             "success": False,
#             "app_id": "fb610534bd5b4951ba9b1dc0bee1713b",
#             "knowledge_base_id": "jnulz2d020"
#         }), 500


@app.route("/pedu/test", methods=["GET"])
def pedu_test():
    """教育版应用ID测试接口"""
    try:
        # 简单测试调用
        result = call_pedu_application("你是谁？")

        return jsonify({
            "success": result.get("success", False),
            "output": result.get("output", {}).get("text", "") if result.get("success") else "",
            "error": result.get("error", "") if not result.get("success") else "",
            "app_id": "fb610534bd5b4951ba9b1dc0bee1713b",
            "knowledge_base_id": "jnulz2d020",
            "api_key_configured": bool(os.getenv("ALIYUN_API_KEY"))
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "app_id": "fb610534bd5b4951ba9b1dc0bee1713b",
            "knowledge_base_id": "jnulz2d020",
            "api_key_configured": bool(os.getenv("ALIYUN_API_KEY"))
        }), 500




@app.route("/performance", methods=["GET"])
def performance_stats():
    """性能统计接口"""
    stats = {
        "timestamp": time.time(),
        "cache_stats": {
            "size": len(optimizer.cache),
            "ttl": optimizer.cache_ttl
        },
        "api_performance": monitor.get_summary()
    }
    return jsonify(stats)


# ==================== Word工具反向代理 ====================
WORD_SERVICE_URL = os.getenv("WORD_SERVICE_URL", "http://localhost:3001")

@app.route("/word", defaults={"subpath": ""}, strict_slashes=False)
@app.route("/word/<path:subpath>", strict_slashes=False)
def word_proxy(subpath):
    """反向代理到 Word 文档填充工具的 Node.js 服务"""
    target_url = f"{WORD_SERVICE_URL}/{subpath}" if subpath else WORD_SERVICE_URL
    method = request.method.lower()


    # 构建 headers，移除 Host 和 Transfer-Encoding
    headers = dict(request.headers)
    headers.pop("Host", None)
    headers.pop("Transfer-Encoding", None)

    try:
        resp = requests.request(
            method=method,
            url=target_url,
            headers=headers,
            params=request.args,
            data=request.get_data(),
            cookies=request.cookies,
            timeout=30,
            stream=True
        )

        excluded_headers = [
            "transfer-encoding", "content-encoding", "connection",
            "keep-alive", "proxy-authenticate", "proxy-authorization",
            "te", "trailers", "upgrade"
        ]
        response_headers = [
            (k, v) for k, v in resp.headers.items()
            if k.lower() not in excluded_headers
        ]

        return Response(
            resp.iter_content(chunk_size=10*1024),
            status=resp.status_code,
            headers=response_headers,
            content_type=resp.headers.get("Content-Type", "application/octet-stream")
        )
    except requests.exceptions.ConnectionError:
        logger.error(f"Word服务连接失败: {WORD_SERVICE_URL}")
        return render_template("word_service_down.html"), 503
    except Exception as e:
        logger.error(f"Word服务代理异常: {e}")
        return jsonify({"error": f"Word服务代理失败: {str(e)}"}), 502


@app.route("/word/health")
def word_health_check():
    """检查Word工具的服务状态"""
    word_status = "unavailable"
    try:
        resp = requests.get(f"{WORD_SERVICE_URL}/health", timeout=3)
        if resp.status_code == 200:
            word_status = "available"
    except:
        pass
    return jsonify({
        "word_service": word_status,
        "word_service_url": WORD_SERVICE_URL,
        "flask_port": int(os.environ.get("PORT", 5004))
    })

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5004))
    logger.info(f"🚀 启动AI张老师服务，端口: {port}")
    logger.info(f"   Word服务地址: {WORD_SERVICE_URL}")
    logger.info(f"   数据库: SQLite (app.db)")
    logger.info(f"   登录页面: http://localhost:{port}/login")
    logger.info(f"   密码登录测试: testuser / test123")
    logger.info(f"   手机验证码测试: 13800138000（验证码见终端输出）")
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)
