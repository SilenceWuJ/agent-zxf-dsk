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
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

from services.rag_service import search_knowledge
from services.llm_service_improved import ask_llm
from services.tts_service import text_to_speech
from services.session_service import get_session, save_session
from services.filter_service import is_related_question
from utils.cache_improved import get_cache, set_cache
from utils.performance import monitor, optimizer, time_it
from utils.logger import logger

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# ==================== 配置区域 ====================
# DeepSeek API - 从环境变量读取
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# 阿里云百炼知识库配置
ALIYUN_API_KEY = os.getenv("ALIYUN_API_KEY")
ALIYUN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID", "7lef75e879")

# 语音合成配置
TTS_VOICE = "longanyang"
TTS_MODEL = "cosyvoice-v3-flash"
TTS_FORMAT = "mp3"

# 系统提示词 - 优化版本，去掉动作描述
SYSTEM_PROMPT = """
你是AI张老师，基于张雪峰风格的高考与考研志愿规划专家。你说话幽默、直率、充满激情，常用具体案例和对比来帮助普通家庭的孩子做出务实选择。

核心原则：
1. 以就业为导向，帮助考生找到有专业壁垒、适合普通家庭投入的方向
2. 不回避现实：谈薪资、谈就业率、谈行业潜规则
3. 对普通家庭孩子要务实，对富裕家庭可以谈兴趣和长远发展

表达风格：
- 经常用"我跟你说啊"、"你记住"、"我告诉你"开头
- 适当使用东北口音词汇（如"整"、"老好了"）
- 语气坚定，结论明确
- 喜欢用具体例子说明问题
- 不要使用动作描述（如拍桌子、扶眼镜等），只使用语言表达

回答规则：
1. 只回答与以下主题相关的问题：
   - 高考志愿填报
   - 考研选择与准备
   - 专业分析与比较
   - 就业前景与薪资
   - 职业规划与发展
   - 院校选择与评估
   - 学习方法与技巧

2. 如果用户问的问题在你的知识范围内，基于知识库回答
3. 如果知识库中没有相关内容，诚实地说"这个我不太确定，但我可以给你一个参考思路"
4. 对于非相关主题的问题，礼貌拒绝
"""

# ==================== 优化函数 ====================

@time_it
def optimized_search_knowledge(question: str) -> str:
    """优化的知识库搜索函数"""
    cache_key = f"rag:{question[:50]}"
    
    # # 尝试从缓存获取
    # cached_result = get_cache(cache_key)
    # if cached_result:
    #     logger.info(f"RAG缓存命中: {question[:30]}...")
    #     return cached_result
    
    # 执行搜索
    monitor.start_timer("rag_search")
    try:
        result = search_knowledge(question)
        monitor.end_timer("rag_search")
        
        # 缓存结果
        if result:
            set_cache(cache_key, result, expire=30)  # 缓存5分钟
        
        return result
    except Exception as e:
        monitor.end_timer("rag_search")
        logger.error(f"RAG搜索失败: {e}")
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


def parallel_api_calls(question: str, need_audio: bool = True) -> dict:
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
        "errors": []
    }
    
    # 第一阶段：并行执行RAG和获取会话历史
    with ThreadPoolExecutor(max_workers=2) as executor:
        # 提交RAG任务
        rag_future = executor.submit(optimized_search_knowledge, question)
        
        # 提交获取会话历史任务
        session_id = str(uuid.uuid4())
        history_future = executor.submit(get_session, session_id)
        
        # 等待结果
        try:
            results["rag_result"] = rag_future.result(timeout=10)
        except Exception as e:
            logger.error(f"RAG任务失败: {e}")
            results["errors"].append(f"RAG失败: {e}")
        
        try:
            history = history_future.result(timeout=5)
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
    
    # 第三阶段：如果需要音频，执行TTS合成
    if need_audio and results["llm_result"]:
        try:
            results["tts_result"] = optimized_text_to_speech(results["llm_result"])
        except Exception as e:
            logger.error(f"TTS合成失败: {e}")
            results["errors"].append(f"TTS失败: {e}")
    
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
        
        # 检查缓存
        cache_key = f"chat:{user_question}"
        cached_response = get_cache(cache_key)
        if cached_response:
            logger.info(f"完整响应缓存命中: {user_question[:30]}...")
            return jsonify(cached_response)
        
        # 执行并行API调用
        logger.info(f"开始处理问题: {user_question[:50]}...")
        api_results = parallel_api_calls(user_question, need_audio)
        
        # 构建响应
        response_data = {
            "answer": api_results["llm_result"],
            "session_id": str(uuid.uuid4()),
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
def index():
    """主页面"""
    return render_template("index.html")


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


if __name__ == "__main__":
    logger.info("启动优化版AI张老师服务...")
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)