"""
This module defines the core setup functions for initializing and configuring
the Flask application. These functions are used in the `app_instance.py` file
to create a singleton instance of the Flask app and integrate supporting
components like Redis, database tables, and logging.
"""

import os
from flask import Flask, abort, request
from flask_cors import CORS
from .routes import APIRoutes
from .database.create_table import create_table

from .constants import DB_TABLE_NAME, ALLOWED_ORIGINS, INTERNAL_ORIGINS,\
    VALID_API_KEY
import logging
from .redis_cache import init_redis


# Error for Missing API Key's
class MissingAPIKeyError(Exception):
    pass


# App Initialization
def create_app():
    """
    Factory function to create and configure the Flask application.

    This function sets up the Flask app with templates, static files, logging,
    routing, database configuration, asynchronous task processing using Celery,
    and caching using Redis.

    Steps performed:
    1. Initializes logging for the application.
    2. Configures the Flask application with:
       - Template and static folder paths.
       - Logging for initialization events.
    3. Retrieves and validates the HuggingFace API key from environment variables.
    4. Registers API routes from the `APIRoutes` blueprint.
    5. Initializes the database and optionally creates a table if required
       (based on the `FLASK_RUN_MAIN` environment variable).
    6. Configures Celery for asynchronous task processing if a broker URL is provided.
    7. Initializes Redis for caching using the specified Redis URL.

    Example:
        >>> from my_app import create_app
        >>> app = create_app()
    """
    # Setup Logging
    _setup_logging()

    # Create the Flask app instance
    app = _init_flask_app()

    model_key = os.getenv("MISTRAL_API_KEY")
    if not model_key:
        app.logger.critical("MISTRAL_API_KEY environment variable is not set.")
        raise MissingAPIKeyError("MISTRAL_API_KEY environment variable not set")

    # Register routes from the APIRoutes blueprint
    try:
        api_routes = APIRoutes()
        app.register_blueprint(api_routes.api_routes_bp)
        app.logger.info("API routes blueprint registered successfully.")
    except Exception as e:
        app.logger.critical(f"Error registering API routes blueprint: {e}")
        raise Exception(f"ERROR: registering API routes: {e}")

    # Build tables if this is main app (i.e. not a celery worker)
    if os.getenv("FLASK_RUN_MAIN") == "1":
        try:
            create_table(DB_TABLE_NAME)
            app.logger.info("Successfully set up database tables")
        except Exception as e:
            raise Exception(f"ERROR: creating database table: {e}")

    # Adding Async capability to the app
    celery_broker_url = os.getenv('CELERY_BROKER_URL')
    if not celery_broker_url:
        app.logger.warning("CELERY_BROKER_URL is not set. Async tasks will \
                           not be available.")
    else:
        app.config['CELERY_BROKER_URL'] = celery_broker_url
        app.config['RESULT_BACKEND'] = os.getenv('RESULT_BACKEND')
        app.logger.info("Celery successfully configured with broker: %s",
                        celery_broker_url)

    # Setting up CORS and authorization
    app.logger.debug("Setting up CORS")
    CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}})
    app.logger.info("CORS successfully setup")

    # Authorization before route access
    @app.before_request
    def validate_origin():
        # Define allowed origins
        origin = request.headers.get("Origin")  # Check where requests comes from
        if not origin:  # If no origin, make sure its internal request
            if (request.remote_addr not in INTERNAL_ORIGINS) and (request.host not in INTERNAL_ORIGINS):  # Replace with trusted IPs # noqa: E501
                app.logger.warning(f"Blocked request with no Origin\
                    header (IP: {request.remote_addr}) (HOST: {request.host})")
                abort(403)  # Forbidden
            else:  # Internal/docker process
                return  # allow

        # Block requests if the origin is not allowed
        if origin:  # If origin
            if origin not in ALLOWED_ORIGINS:  # If not pre-approved, require API key
                api_key = request.headers.get("Authorization")  # get key

                # if no key/wrong key
                if not api_key or api_key.split("Bearer ")[-1] != VALID_API_KEY:
                    app.logger.warning("Blocked request from disallowed origin \
                                       without API_KEY: %s", origin)
                    abort(401)  # Unauthorized: Missing or invalid API key
                else:  # correct key for unapproved origin
                    return  # allow
            else:  # if in pre-approved list
                return  # allow

    # Initialize Redis for Caching
    init_redis(app, os.getenv("REDIS_DB_CACHE_URL"))

    app.logger.info("Application sucessfully created")
    return app


# Helpers for create_app()
def _setup_logging():
    """
    Configures the logging for the application.

    Example:
        >>> setup_logging()
        2023-12-04 12:00:00,000 - root - INFO - Logging is set up.
    """
    log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logging.info("Logging is set up.")


def _init_flask_app():
    """
    Configures the flask application

    """
    app = Flask(__name__)
    app.config['ENV'] = 'development'
    app.config['DEBUG'] = True
    app.config['TESTING'] = True
    app.logger.info(f"Flask application instance created.")
    return app
