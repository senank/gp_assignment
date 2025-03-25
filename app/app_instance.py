"""
This module initializes and configures the main application components.

It creates a singleton instance of the Flask application based on `FLASK_APP_MAIN`
using `create_app` and sets up the Celery worker instance using `make_celery`, ensuring
the application and task queue are properly integrated.
"""

from app import create_app
from .celery_worker import make_celery

from redis.exceptions import ConnectionError as RedisConnectionError
import threading
from time import sleep
import os

from logging import getLogger


logger = getLogger(__name__)

app = create_app()  # Singleton instance of the Flask app
celery = make_celery(app)


def _update_health_status():
    """
    Runs in the background and updates Redis & Celery health status every 5s.
    """
    while True:
        try:
            redis_client = app.config["REDIS_CACHE"]
            redis_client.set("redis_status", "up", ex=15)  # Expire in 15s
            redis_client_up = True
            logger.info("Redis is up.")
        except (Exception, RedisConnectionError):
            logger.warning("Redis ping failed, Redis is down.")
            redis_client_up = False

        if redis_client_up:
            try:
                workers = celery.control.ping(timeout=3)
                if bool(workers) is False:
                    redis_client.set("celery_status", "down", ex=15)
                    logger.info("Celery workers are down.")
                else:
                    redis_client.set("celery_status", "up", ex=15)
                    logger.info("Celery workers are up.")
            except Exception:
                redis_client.set("celery_status", "down", ex=15)
                logger.info("Celery workers are down.")

        sleep(10)  # Check every 10 seconds


if os.getenv("FLASK_RUN_MAIN") == "1":
    health_thread = threading.Thread(target=_update_health_status, daemon=True)
    health_thread.start()
    logger.info("started health check loop")
