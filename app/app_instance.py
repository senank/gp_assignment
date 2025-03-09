"""
This module initializes and configures the main application components.

It creates a singleton instance of the Flask application based on `FLASK_APP_MAIN`
using `create_app` and sets up the Celery worker instance using `make_celery`, ensuring
the application and task queue are properly integrated.
"""

from app import create_app
from .celery_worker import make_celery

import redis
import threading
import time
import os

from logging import getLogger


logger = getLogger(__name__)

app = create_app()  # Singleton instance of the Flask app
celery = make_celery(app)

redis_client = redis.Redis(host="redis", port=6379, db=0)


def _update_health_status():
    """
    Runs in the background and updates Redis & Celery health status every 5s.
    """
    while True:
        try:
            redis_client.set("redis_status", "up", ex=15)  # Expire in 10s
        except Exception:
            redis_client.set("redis_status", "down", ex=15)

        try:
            workers = celery.control.ping(timeout=3)
            if bool(workers) is False:
                redis_client.set("celery_status", "down", ex=15)
            else:
                redis_client.set("celery_status", "up", ex=15)
        except Exception:
            redis_client.set("celery_status", "down", ex=15)

        time.sleep(10)  # Check every 10 seconds


if os.getenv("FLASK_RUN_MAIN") == "1":
    health_thread = threading.Thread(target=_update_health_status, daemon=True)
    health_thread.start()
    logger.info("started health check loop")
