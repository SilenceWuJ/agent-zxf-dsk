#!/usr/bin/env python
# -*- coding: utf-8 -*-
# utils/cache.py

import redis
import json

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 0

try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True
    )
except Exception:
    redis_client = None


def get_cache(key):

    if not redis_client:
        return None

    try:
        value = redis_client.get(key)

        if value:
            return json.loads(value)

    except Exception:
        return None

    return None


def set_cache(key, value, expire=3600):

    if not redis_client:
        return

    try:
        redis_client.set(
            key,
            json.dumps(value),
            ex=expire
        )

    except Exception:
        pass