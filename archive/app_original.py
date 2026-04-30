#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import requests
import base64
import time
import uuid
from flask import Flask, request, jsonify, send_file, render_template
from dotenv import load_dotenv
from services.rag_service import search_knowledge
from services.llm_service import ask_llm
from utils.logger import get_logger
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer, ResultCallback
from services.tts_service import text_to_speech
from services.session_service import get_session, save_session

from utils.cache import get_cache, set_cache
from utils.performance import monitor, optimizer, time_it

# 加载环境变量
load_dotenv()
logger = get_logger()


app = Flask(__name__)

# ==================== 配置区域 ====================
# DeepSeek API - 从环境变量读取
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# 阿里云百炼知识库配置
# 注意：阿里云Responses API需要使用OpenAI SDK兼容模式
ALIYUN_API_KEY = os.getenv("ALIYUN_API_KEY")  # 从环境变量读取
ALIYUN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID", "7lef75e879")  # 从环境变量读取，有默认值

# 腾讯云语音克隆配置（可选）
# TENCENT_SECRET_ID = os.getenv("TENCENT_SECRET_ID")
# TENCENT_SECRET_KEY = os.getenv("TENCENT_SECRET_KEY")
# TENCENT_SDK_APP_ID = os.getenv("TENCENT_SDK_APP_ID")
# VOICE_ID = os.getenv("VOICE_ID")

# 阿里云 DashScope 配置（用于语音合成）
# 注意：如果使用阿里云百炼 API Key，则与 ALIYUN_API_KEY 相同
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", ALIYUN_API_KEY)

# 语音合成配置
TTS_VOICE = "longanyang"  # 音色，可更换为其他支持的音色
TTS_MODEL = "cosyvoice-v3-flash"  # 模型，推荐使用 cosyvoice-v3-flash
TTS_FORMAT = "mp3"  # 输出格式：mp3 或 wav

# 设置 DashScope API Key
dashscope.api_key = DASHSCOPE_API_KEY

# 以下为新加坡地区 URL，国内用户需替换为：wss://dashscope.aliyuncs.com/api-ws/v1/inference
dashscope.base_websocket_api_url = 'wss://dashscope.aliyuncs.com/api-ws/v1/inference'

# ================================================

# 检查必要的环境变量
def check_environment_variables():
    """检查必要的环境变量是否已设置"""
    missing_vars = []
    
    if not DEEPSEEK_API_KEY:
        missing_vars.append("DEEPSEEK_API_KEY")
    
    if not ALIYUN_API_KEY:
        missing_vars.append("ALIYUN_API_KEY")
    
    if missing_vars:
        error_msg = f"缺少必要的环境变量: {', '.join(missing_vars)}\n"
        error_msg += "请创建.env文件并设置以下环境变量：\n"
        error_msg += "DEEPSEEK_API_KEY=你的DeepSeek API密钥\n"
        error_msg += "ALIYUN_API_KEY=你的阿里云API密钥\n"
        error_msg += "KNOWLEDGE_BASE_ID=你的知识库ID（可选）\n"
        raise ValueError(error_msg)
    
    print("✅ 环境变量检查通过")
    print(f"📊 配置信息:")
    print(f"   - DeepSeek API: {'已配置' if DEEPSEEK_API_KEY else '未配置'}")
    print(f"   - 阿里云API: {'已配置' if ALIYUN_API_KEY else '未配置'}")
    print(f"   - 知识库ID: {KNOWLEDGE_BASE_ID}")

# 在应用启动时检查环境变量
try:
    check_environment_variables()
except ValueError as e:
    print(f"⚠️  环境变量配置警告: {e}")
    print("应用将继续运行，但部分功能可能不可用")

# AI张老师人设提示词
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
4. 对于非相关主题的问题（如天气、娱乐、政治、个人生活等），礼貌拒绝：
   "这个问题超出了我的专业范围。我是专门帮助大家解决高考志愿、考研选择和职业规划问题的。你有什么关于专业选择或就业方面的问题吗？"
"""


# def is_related_question(question):
#     """判断问题是否与专业/考研/就业相关"""
#     # 相关关键词列表
#     related_keywords = [
#         # 高考相关
#         '高考', '志愿', '填报', '分数线', '录取', '大学', '院校', '本科', '专科',
#         '一本', '二本', '三本', '985', '211', '双一流', '分数线', '录取线','报考'
#
#         # 考研相关
#         '考研', '研究生', '硕士', '博士', '保研', '推免', '复试', '初试',
#         '专业课', '公共课', '导师', '研究方向', '学术', '论文',
#
#         # 专业相关
#         '专业', '学科', '课程', '计算机', '软件', '工程', '医学', '法律',
#         '金融', '经济', '管理', '教育', '艺术', '设计', '建筑', '机械',
#         '电子', '电气', '自动化', '化学', '物理', '数学', '生物', '环境',
#
#         # 就业相关
#         '就业', '工作', '职业', '薪资', '工资', '待遇', '前景', '发展',
#         '行业', '企业', '公司', '招聘', '面试', '简历', '技能', '能力',
#
#         # 学习相关
#         '学习', '方法', '技巧', '效率', '备考', '复习', '考试', '成绩',
#
#         # 规划相关
#         '规划', '选择', '方向', '未来', '发展', '建议', '咨询', '指导'
#     ]
#
#     question_lower = question.lower()
#
#     # 检查是否包含相关关键词
#     for keyword in related_keywords:
#         if keyword in question_lower:
#             return True
#
#     # 检查常见问题模式
#     patterns = [
#         r'.*怎么选.*专业.*',
#         r'.*什么专业.*好.*',
#         r'.*哪个.*大学.*好.*',
#         r'.*就业.*怎么样.*',
#         r'.*薪资.*多少.*',
#         r'.*前景.*如何.*',
#         r'.*适合.*学.*什么.*',
#         r'.*推荐.*专业.*',
#         r'.*比较.*专业.*',
#         r'.*分析.*专业.*'
#     ]
#
#     import re
#     for pattern in patterns:
#         if re.match(pattern, question_lower):
#             return True
#
#     return False


def get_rag_response(user_question):
    """使用阿里云Responses API进行RAG检索+生成"""
    if not ALIYUN_API_KEY:
        print("⚠️  阿里云API密钥未配置，跳过知识库检索")
        return ""
    
    try:
        # 使用requests直接调用API，避免Unicode编码问题
        import json
        
        headers = {
            "Authorization": f"Bearer {ALIYUN_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "qwen-plus",  # 使用qwen-plus模型
            "input": user_question,
            "tools": [
                {
                    "type": "file_search",
                    "vector_store_ids": [KNOWLEDGE_BASE_ID]
                }
            ],
            "instructions": SYSTEM_PROMPT
        }
        
        response = requests.post(
            f"{ALIYUN_BASE_URL}/responses",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        # 处理返回的文本，确保正确解码
        if "output" in result and "text" in result["output"]:
            output_text = result["output"]["text"]
            # 确保返回的是字符串，不是Unicode编码
            if isinstance(output_text, str):
                return output_text
            else:
                # 如果是其他类型，转换为字符串
                return str(output_text)
        else:
            print(f"⚠️  阿里云API返回格式异常: {result}")
            return ""
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️  阿里云API请求失败: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"响应内容: {e.response.text}")
        return ""
    except Exception as e:
        print(f"⚠️  知识库检索失败: {e}")
        return ""


def call_deepseek_with_context(question, context):
    """调用DeepSeek，传入检索到的上下文"""
    if not DEEPSEEK_API_KEY:
        raise ValueError("DeepSeek API密钥未配置")
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""已知信息：
{context}

用户问题：{question}

请基于以上已知信息，用AI张老师的风格回答用户问题。"""

    payload = {
        "model": "deepseek-v4-pro",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1024
    }

    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"❌ DeepSeek API请求失败: {e}")
        raise
    except KeyError as e:
        print(f"❌ DeepSeek API响应格式错误: {e}")
        print(f"响应内容: {response.text}")
        raise

def text_to_speech_aliyun(text):
    """
    使用阿里云 DashScope 语音合成
    返回音频二进制数据
    """
    try:
        # 如果文本过长（超过20000字符），需要截断
        if len(text) > 20000:
            text = text[:19950] + "..."

        # 创建合成器实例
        synthesizer = SpeechSynthesizer(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            format=TTS_FORMAT  # 支持 'mp3', 'wav', 'pcm'
        )

        # 调用合成，获取结果对象
        result = synthesizer.call(text)
        
        # 检查结果对象
        if hasattr(result, 'get_audio_data'):
            # 新版本SDK：使用 get_audio_data() 方法
            audio_data = result.get_audio_data()
        elif hasattr(result, 'audio_data'):
            # 旧版本SDK：直接访问 audio_data 属性
            audio_data = result.audio_data
        elif hasattr(result, 'output'):
            # 另一种可能的格式
            audio_data = result.output
        else:
            # 如果都不行，尝试直接使用结果
            audio_data = result
        
        # 确保返回的是字节数据
        if isinstance(audio_data, bytes):
            print(f"语音合成成功，音频大小: {len(audio_data)} bytes")
            return audio_data
        elif isinstance(audio_data, str):
            # 如果是字符串，转换为字节
            print(f"语音合成返回字符串，长度: {len(audio_data)} 字符")
            return audio_data.encode('utf-8')
        elif audio_data is None:
            print("语音合成返回 None")
            return None
        else:
            # 尝试转换为字节
            print(f"语音合成返回类型: {type(audio_data)}")
            try:
                audio_bytes = bytes(audio_data)
                print(f"成功转换为字节，大小: {len(audio_bytes)} bytes")
                return audio_bytes
            except:
                print(f"无法转换为字节，返回 None")
                return None

    except Exception as e:
        print(f"语音合成失败: {e}")
        import traceback
        traceback.print_exc()
        return None
def text_to_speech_with_callback(text):
    """
    使用回调方式的语音合成（流式输出，适合长文本）
    返回完整的音频二进制数据
    """
    try:
        # 定义回调类
        class MyCallback(ResultCallback):
            def __init__(self):
                self.audio_chunks = []
                self.complete = False

            def on_open(self):
                print("WebSocket 连接已建立")

            def on_complete(self):
                print("语音合成完成")
                self.complete = True

            def on_error(self, message):
                print(f"语音合成错误: {message}")

            def on_close(self):
                print("连接已关闭")

            def on_data(self, data: bytes):
                # 接收音频数据块
                self.audio_chunks.append(data)

        callback = MyCallback()

        # 创建合成器（带回调）
        synthesizer = SpeechSynthesizer(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            format=TTS_FORMAT,
            callback=callback
        )

        # 执行合成
        synthesizer.call(text)

        # 等待合成完成
        import time
        start_time = time.time()
        while not callback.complete and time.time() - start_time < 30:  # 30秒超时
            time.sleep(0.1)

        # 合并所有音频块
        if callback.audio_chunks:
            audio_data = b''.join(callback.audio_chunks)
            print(f"流式语音合成成功，音频大小: {len(audio_data)} bytes")
            return audio_data
        else:
            print("流式语音合成未收到音频数据")
            return None

    except Exception as e:
        print(f"流式语音合成失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def text_to_speech_simple(text):
    """
    简单的语音合成函数，使用requests直接调用阿里云API
    避免DashScope SDK的兼容性问题
    """
    try:
        # 如果文本过长，需要截断
        if len(text) > 20000:
            text = text[:19950] + "..."
        
        # 阿里云语音合成API URL - 使用正确的API端点
        # 根据阿里云文档：https://help.aliyun.com/zh/model-studio/developer-reference/tts-api
        tts_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/tts"
        
        headers = {
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": TTS_MODEL,
            "input": {
                "text": text
            },
            "parameters": {
                "voice": TTS_VOICE,
                "format": TTS_FORMAT,
                "sample_rate": 16000,
                "word_count_limit": 20000
            }
        }
        
        print(f"调用阿里云TTS API，文本长度: {len(text)} 字符")
        response = requests.post(tts_url, headers=headers, json=payload, timeout=30)
        print(f"API响应状态码: {response.status_code}")
        
        response.raise_for_status()
        
        # 阿里云语音合成API返回的是音频二进制数据
        audio_data = response.content
        
        if audio_data and len(audio_data) > 0:
            print(f"直接API语音合成成功，音频大小: {len(audio_data)} bytes")
            return audio_data
        else:
            print("直接API语音合成返回空数据")
            return None
            
    except Exception as e:
        print(f"直接API语音合成失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def text_to_speech_fallback(text):
    """
    备用的语音合成函数，使用更简单的实现
    如果其他方法都失败，使用这个
    """
    try:
        # 如果文本过长，需要截断
        if len(text) > 1000:
            text = text[:950] + "..."
        
        print(f"使用备用语音合成，文本长度: {len(text)} 字符")
        
        # 这里可以添加其他语音合成服务的实现
        # 例如：使用本地TTS库、其他云服务等
        
        # 暂时返回None，表示不支持语音合成
        print("备用语音合成：当前未实现")
        return None
        
    except Exception as e:
        print(f"备用语音合成失败: {e}")
        return None

def text_to_speech(text):
    """
    语音合成函数 - 暂时禁用，专注于核心功能
    """
    print(f"语音合成功能暂时禁用，文本长度: {len(text)} 字符")
    print("提示：语音合成需要正确的阿里云API密钥和配置")
    return None



@app.route("/chat", methods=["POST"])
def chat():
    """主对话接口：接收文本/音频，返回文本+音频"""
    start = time.time()
    data = request.get_json()
    user_question = data.get("question", "")
    need_audio = data.get("need_audio", True)  # 是否返回音频，默认返回
    session_id = data.get("session_id")

    if not session_id:
        session_id = str(uuid.uuid4())

    cache_key = f"qa:{user_question}"

    cached = get_cache(cache_key)
    if cached:
        cached["session_id"] = session_id
        return jsonify(cached)

    if not user_question:
        return jsonify({"error": "请输入问题"}), 400

    # 检查问题是否相关
    # if not is_related_question(user_question):
    #     print(f"⚠️  非相关问题被过滤: {user_question}")
    #     return jsonify({
    #         "answer": "这个问题超出了我的专业范围。我是专门帮助大家解决高考志愿、考研选择和职业规划问题的。你有什么关于专业选择或就业方面的问题吗？",
    #         "filtered": True
    #     })

    try:
        # 1. 从阿里云知识库检索相关上下文
        # context = get_rag_response(user_question)
        
        # 2. 调用大模型生成回答
        # answer = call_deepseek_with_context(user_question, context)

        history = get_session(session_id)

        context = search_knowledge(user_question)

        answer = ask_llm(user_question, context, history)

        history.append({"role": "user", "content": user_question})

        history.append({"role": "assistant", "content": answer})

        save_session(session_id, history)


        # 3. 语音合成
        audio_base64 = None
        if need_audio:
            try:
                print(f"开始语音合成，文本长度: {len(answer)} 字符")
                audio_bytes = text_to_speech(answer)
                if audio_bytes:
                    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                    print(f"语音合成成功，base64长度: {len(audio_base64)} 字符")
                else:
                    print("语音合成返回None")
            except Exception as e:
                print(f"语音合成失败: {e}")
                import traceback
                traceback.print_exc()

        # 返回结果
        response_data = {
            "answer": answer,
            "audio": audio_bytes,
            "session_id": session_id
        }

        set_cache(cache_key, response_data)
        if audio_base64:
            response_data["audio_base64"] = audio_base64
            response_data["audio_format"] = TTS_FORMAT

        print(f"返回数据: answer长度={len(answer)}, audio={'有' if audio_base64 else '无'}")

        set_cache(cache_key, response_data)

        logger.info(f"question={user_question}")

        logger.info(f"time={time.time() - start}")

        return jsonify(response_data)

        
    except ValueError as e:
        # API密钥缺失错误
        error_msg = str(e)
        if "API密钥未配置" in error_msg:
            return jsonify({
                "error": "服务配置不完整",
                "message": "请检查API密钥配置",
                "answer": "抱歉，服务暂时无法使用。请检查API密钥配置。"
            }), 503
        else:
            return jsonify({"error": str(e)}), 500
            
    except Exception as e:
        print(f"聊天接口异常: {e}")
        return jsonify({
            "error": "内部服务器错误",
            "message": str(e),
            "answer": "抱歉，AI张老师暂时无法回答。请稍后再试！"
        }), 500


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/old", methods=["GET"])
def old_index():
    """保留原始简单版本"""
    return send_file("main.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)