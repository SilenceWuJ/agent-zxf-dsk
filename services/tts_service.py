#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import base64
from config import ALIYUN_API_KEY,TTS_MODEL,TTS_VOICE


def text_to_speech(text):

    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/tts"

    headers = {
        "Authorization": f"Bearer {ALIYUN_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model":TTS_MODEL,
        "input":{"text":text},
        "parameters":{
            "voice":TTS_VOICE,
            "format":"mp3"
        }
    }

    r = requests.post(url,headers=headers,json=payload)

    if r.status_code == 200:

        return base64.b64encode(r.content).decode()

    return None