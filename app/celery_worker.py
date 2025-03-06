"""
This module defines the `make_celery` function for initializing a Celery instance
configured to work with the Flask application. It binds the Flask app context
to Celery tasks, ensuring that tasks have access to the app's configuration and
context during execution.
"""

from celery import Celery
import logging

logger = logging.getLogger(__name__)


def make_celery(app):
    """
    Factory function to configure and return a Celery instance integrated with
    a Flask app.

    This function sets up a Celery worker by:
    1. Using the Flask app's configuration for the result backend and broker URL.
    2. Updating the Celery configuration with the app's settings.
    3. Ensuring the worker retries broker connections on startup.
    4. Binding the Flask app's context to Celery tasks to allow them to access
        the app's resources.

    Example:
        >>> from app import create_app
        >>> from celery_worker import make_celery
        >>> app = create_app()
        >>> celery = make_celery(app)
        >>> @celery.task
        >>> def add(x, y):
        >>>     return x + y
    """
    logger.info("Starting up Celery")
    celery = Celery(
        app.import_name,
        backend=app.config.get('RESULT_BACKEND'),
        broker=app.config.get('CELERY_BROKER_URL')
    )
    celery.conf.update(app.config)
    celery.conf.update({
        'broker_connection_retry_on_startup': True,  # Celery retries on startup
    })

    # Bind Flask app context to Celery tasks
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
