#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import requests
import base64
from flask import Flask, request, jsonify, send_file, render_template
from dotenv import load_dotenv
# from tencentcloud.common import credential
# from tencentcloud.trtc.v20190722 import trtc_client, models
import io
import wave
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer, ResultCallback
# 加载环境变量
load_dotenv()

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

回答规则：
- 如果用户问的问题在你的知识范围内，基于知识库回答
- 如果知识库中没有相关内容，诚实地说"这个我不太确定，但我可以给你一个参考思路"
- 对于恶意或无关问题，引导回志愿规划主题
"""


def get_rag_response(user_question):
    """使用阿里云Responses API进行RAG检索+生成"""
    if not ALIYUN_API_KEY:
        print("⚠️  阿里云API密钥未配置，跳过知识库检索")
        return ""
    
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=ALIYUN_API_KEY,
            base_url=ALIYUN_BASE_URL
        )

        response = client.responses.create(
            model="qwen3.5-plus",  # 或 qwen3.5-flash 更便宜
            input=user_question,
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [KNOWLEDGE_BASE_ID]
                }
            ],
            # 注入AI张老师人设
            instructions=SYSTEM_PROMPT
        )

        return response.output_text
    except ImportError:
        print("⚠️  OpenAI库未安装，无法使用阿里云知识库")
        print("   请运行: pip install openai")
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
        "model": "deepseek-chat",
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
        # 如果文本过长（超过20000字符），需要截断[citation:3]
        if len(text) > 20000:
            text = text[:19950] + "..."

        # 创建合成器实例
        synthesizer = SpeechSynthesizer(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            format=TTS_FORMAT  # 支持 'mp3', 'wav', 'pcm'
        )

        # 调用合成，获取音频二进制数据
        audio_data = synthesizer.call(text)

        print(f"语音合成成功，音频大小: {len(audio_data)} bytes")
        return audio_data

    except Exception as e:
        print(f"语音合成失败: {e}")
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

        # 合并所有音频块
        if callback.audio_chunks:
            return b''.join(callback.audio_chunks)
        return None

    except Exception as e:
        print(f"流式语音合成失败: {e}")
        return None


# 选择使用哪个合成函数（简单版或流式版）
text_to_speech = text_to_speech_aliyun



@app.route("/chat", methods=["POST"])
def chat():
    """主对话接口：接收文本/音频，返回文本+音频"""
    data = request.get_json()
    user_question = data.get("question", "")
    need_audio = data.get("need_audio", True)  # 是否返回音频，默认返回

    if not user_question:
        return jsonify({"error": "请输入问题"}), 400

    try:
        # 1. 从阿里云知识库检索相关上下文
        context = get_rag_response(user_question)
        
        # 2. 调用大模型生成回答
        answer = call_deepseek_with_context(user_question, context)

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
            "answer": answer
        }
        if audio_base64:
            response_data["audio_base64"] = audio_base64
            response_data["audio_format"] = TTS_FORMAT

        print(f"返回数据: answer长度={len(answer)}, audio={'有' if audio_base64 else '无'}")
        return jsonify(response_data)

        # # 3. 语音合成（可选）
        # audio_base64 = None
        # if TENCENT_SECRET_ID and TENCENT_SECRET_KEY:
        #     try:
        #         audio_bytes = text_to_speech(answer)
        #         audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        #     except Exception as e:
        #         print(f"语音合成失败: {e}")

        # return jsonify({
        #     "answer": answer,
        #     # "audio_base64": audio_base64
        # })
        
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