#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from config import ALIYUN_API_KEY, ALIYUN_BASE_URL, KNOWLEDGE_BASE_ID


def search_knowledge(question):

    headers = {
        "Authorization": f"Bearer {ALIYUN_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "qwen-plus",
        "input": question,
        "tools": [
            {
                "type": "file_search",
                "vector_store_ids": [KNOWLEDGE_BASE_ID]
            }
        ]
    }

    try:

        r = requests.post(
            f"{ALIYUN_BASE_URL}/responses",
            headers=headers,
            json=payload,
            timeout=30
        )

        r.raise_for_status()

        data = r.json()

        texts = []

        for item in data.get("output", []):

            for content in item.get("content", []):

                if content.get("type") == "output_text":

                    texts.append(content.get("text", ""))

        return "\n".join(texts)

    except Exception as e:

        print("RAG ERROR:", e)

        return ""