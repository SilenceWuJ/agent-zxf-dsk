#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

load_dotenv()

# DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# 阿里云
ALIYUN_API_KEY = os.getenv("ALIYUN_API_KEY")
ALIYUN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID")

# TTS
TTS_MODEL = "cosyvoice-v3-flash"
TTS_VOICE = "longanyang"

# redis缓存
REDIS_URL = "redis://localhost:6379"