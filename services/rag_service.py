#!/usr/bin/env python
# -*- coding: utf-8 -*-

from config import ALIYUN_API_KEY, ALIYUN_BASE_URL, KNOWLEDGE_BASE_ID
from openai import OpenAI

def search_knowledge(question):

    client = OpenAI(
        api_key=ALIYUN_API_KEY,
        base_url=ALIYUN_BASE_URL
    )


    try:
        response = client.responses.create(
            model="qwen-plus",
            input=question,
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [KNOWLEDGE_BASE_ID]
                }
            ],
            instructions="你是张雪峰老师，高考志愿规划专家。"
        )
        # print("返回内容:", response.output_text)
        return response.output_text
    except Exception as e:
        print("错误:", e)
        return None