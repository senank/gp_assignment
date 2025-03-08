"""
This module provides utilities for integrating Redis caching into the application. Redis
is used to store and retrieve frequently accessed data to enhance performance and reduce
database load. The module includes functionality for initializing Redis, managing cache
entries, and generating cache keys.

"""
import redis
from typing import Any, Tuple
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


# Getters
def get_cache(redis_client, key: str) -> Tuple[int, Any]:
    """
    Retrieves a string value from the Redis cache for a given key.

    Example:
        >>> status, value = get_cache(redis_client, "my_key")
        >>> if status:
        >>>     print(f"Cached value: {value}")
        >>> else:
        >>>     print("Value not found in cache or Redis is down.")
    """
    try:
        cached_value = redis_client.get(key)
        if cached_value:
            return 1, cached_value
        else:
            return 0, None
    except redis.exceptions.ConnectionError:
        # If Redis is down, skip cache set
        logger.warning("Redis server is down, skipping cache get.")
        return 0, None


# Setters
def set_cache(redis_client, key: str, value: str, **kwargs) -> None:
    """
    Stores a key-value pair in the Redis cache where the value is a string.

    Example:
        >>> set_cache(redis_client, "my_key", "my_value", ex=3600)
    """
    try:
        expiry = kwargs.get('ex', None)
        if expiry:
            redis_client.set(key, value, ex=expiry)
        else:
            redis_client.set(key, value)
        logger.info(f"Successfully added {key} to redis cache")
        return
    except redis.exceptions.ConnectionError:
        # If Redis is down, skip cache set
        logger.warning("Redis server is down, skipping cache set.")
        return


# Generating key's for cache
def cache_key_answer_question(input: str) -> str:
    """
    Generates a cache key for similarity comparison calls.
    """
    cache_str = f"""
    {input}
    """
    return encoded_str(cache_str)


def encoded_str(cache_str: str) -> str:
    """
    Encodes a string using SHA-256 and returns its hexadecimal digest.
    """
    return sha256(cache_str.encode('utf-8')).hexdigest()
