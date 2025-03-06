"""
This module initializes and configures the main application components.

It creates a singleton instance of the Flask application based on `FLASK_APP_MAIN`
using `create_app` and sets up the Celery worker instance using `make_celery`, ensuring
the application and task queue are properly integrated.
"""

from app import create_app
from .celery_worker import make_celery

app = create_app()  # Singleton instance of the Flask app
celery = make_celery(app)
