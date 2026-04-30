#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
from config import DEEPSEEK_API_KEY, DEEPSEEK_URL

SYSTEM_PROMPT = """
你是AI张老师。

模仿张雪峰风格：

特点：

1 直接
2 幽默
3 讲就业
4 举真实案例
5 对普通家庭给务实建议
"""


# def ask_llm(question, context):
#
#     prompt = f"""
# 参考资料：
#
# {context}
#
# 问题：
#
# {question}
#
# 请用张雪峰风格回答
# """
#
#     payload = {
#         "model": "deepseek-v4-pro",
#         "messages": [
#             {"role":"system","content":SYSTEM_PROMPT},
#             {"role":"user","content":prompt}
#         ],
#         "temperature":0.7
#     }
#
#     headers = {
#         "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
#         "Content-Type": "application/json"
#     }
#
#     r = requests.post(
#         DEEPSEEK_URL,
#         headers=headers,
#         json=payload,
#         timeout=30
#     )
#
#     r.raise_for_status()
#
#     return r.json()["choices"][0]["message"]["content"]


def ask_llm(question, context, history):

    messages = []

    for item in history:
        messages.append(item)

    messages.append({
        "role": "user",
        "content": f"""
知识库信息:
{context}

用户问题:
{question}

请用张雪峰风格回答
"""
    })

    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        },
        json={
            "model": "deepseek-v4-pro",
            "messages": messages,
            "temperature": 0.7
        }
    )

    result = response.json()

    return result["choices"][0]["message"]["content"]