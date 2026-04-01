#!/usr/bin/env python
# -*- coding: utf-8 -*-
import redis
import json

redis_client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    decode_responses=True
)

SESSION_EXPIRE = 3600


def get_session(session_id):

    data = redis_client.get(f"session:{session_id}")

    if data:
        return json.loads(data)

    return []


def save_session(session_id, history):

    redis_client.set(
        f"session:{session_id}",
        json.dumps(history),
        ex=SESSION_EXPIRE
    )