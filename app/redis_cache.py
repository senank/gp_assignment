"""
redis_cache.py
===============

This module provides utilities for integrating Redis caching into the application. Redis
is used to store and retrieve frequently accessed data to enhance performance and reduce
database load. The module includes functionality for initializing Redis, managing cache
entries, and generating cache keys.

Module Overview:
----------------
The file is divided into the following sections:
1. **Redis Initialization**: Functions to configure and set up the Redis client.
2. **Getters**: Functions to retrieve cached data.
3. **Setters**: Functions to set cache entries.
4. **Cache Key Generation**: Utilities to generate consistent keys for caching based on
                application logic.

Dependencies:
-------------
- redis: Python Redis client for interacting with the Redis database.
- json: For serializing and deserializing cached data.
- hashlib: For generating consistent hash keys using SHA-256.
- logging: For logging Redis-related operations.
"""
import redis
import json
from typing import Dict, Any, Tuple
from hashlib import sha256
from logging import getLogger


# logging
logger = getLogger(__name__)


# redis_cache initialization
def init_redis(app, redis_url: str) -> None:
    """
    Initializes and configures a Redis caching client for the Flask application.
    """
    try:
        redis_client = redis.Redis.from_url(redis_url)
        app.config["REDIS_CACHE"] = redis_client
        app.logger.info("Redis caching client initialized successfully.")
        return
    except Exception as e:
        app.logger.warning(f"Failed to initialize Redis client: {e}")
        return

