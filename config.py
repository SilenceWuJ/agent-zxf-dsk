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
ALIYUN_APP_ID = os.getenv("ALIYUN_APP_ID", "2b5a7966b6c94f36af8e8c8567fb1357")
# ALIYUN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
ALIYUN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID")
ALIYUN_APP_ID_J = os.getenv("ALIYUN_APP_ID_J", "2b5a7966b6c94f36af8e8c8567fb1357")
KNOWLEDGE_BASE_ID_J = os.getenv("KNOWLEDGE_BASE_ID_J")

# TTS
TTS_MODEL = "cosyvoice-v3-flash"
TTS_VOICE = "longanyang"

# redis缓存
REDIS_URL = "redis://localhost:6379"