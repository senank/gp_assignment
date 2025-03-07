from flask import request, jsonify, Blueprint
from jsonschema import ValidationError

import redis

from .task import emb_and_store
from .extract_pdf import extract_data_from_pdf

import logging
logger = logging.getLogger(__name__)

def _redis_healthcheck():
    """
    Check the availability of the Redis server using the specified host, port,
    and database. `ConnectionError` is raised if unavailable or error occured.
    """
    try:
        redis_client = redis.Redis(host="redis", port=6379, db=0)
        redis_client.ping()
    except Exception as e:
        logger.warning(f"redis_healthcheck: Could not connect to redis: {e}\n")
        raise ConnectionError


def _is_celery_worker_active():
    """
    Attempts to ping celery worker, `ConnectionError` is raised if not successful.
    """
    try:
        from .app_instance import celery
        workers = celery.control.ping(timeout=3)
        logger.debug(f"Workers: {workers}")
        if bool(workers) is False:
            raise ConnectionError
    except Exception:
        raise ConnectionError


# API endpoint class
class APIRoutes:
    """
    A class to define API routes for the application.

    This class sets up the API routes for different endpoints such as add_pdf, and
    compare_id. It uses a Flask Blueprint to manage the routes and associate them with
    their respective view functions.

    Attributes:
        api_routes_bp (Blueprint): A Flask Blueprint object that holds all the API routes.
    """
    def __init__(self):
        """
        Initializes the APIRoutes with the provided client and registers API routes.
        """
        self.api_routes_bp = Blueprint('api_routes', __name__)
        logger.info("Initializing API routes...")

        self.api_routes_bp.add_url_rule('/add_pdf', 'add_pdf', self.add_pdf,
                                        methods=['POST'])
        
        self.api_routes_bp.add_url_rule('/answer_question', 'answer_question',
                                        self.answer_question, methods=['POST'])

        logger.debug("Successfully registered routes")


    # URL/add_pdf
    def add_pdf(self):
        """
        Handles /add_pdf POST requests to extract the data of a pdf, embed it and store
        it in the database
        """
        logger.info("Processing add_pdf request.")
        try:
            # Validate request is a pdf file
            _validate_add_pdf(request)
            logger.debug("Validated file data type")

            # Get bytes from file
            pdf = request.files['file'].read()
            logger.debug("Extracted file bytes")

            # extracting pdf data for storage
            logger.debug(f"Extracting {pdf} to the db.")
            pdf_id, pdf_text = extract_data_from_pdf(pdf)


            # Checking if redis and celery worker available
            logger.debug("Checking if redis are available")
            _redis_healthcheck()  # Healthcheck redis for .delay
            logger.debug("Checking if celery workers are available")
            _is_celery_worker_active()  # Check if celery worker is active
            logger.debug("Redis and Celery available, adding asynchronously")

            emb_and_store.delay(pdf_id, pdf_text)

            logger.info(f"Successfully added pdf ASYNCHRONOUSLY")
            return jsonify({"message": f"Succesfully added pdf"}), 200
        except ConnectionError:
            logger.error("Connection error to redis, adding synchronously")
            logger.debug(f"Adding {pdf_text} to the db.")
            emb_and_store(pdf_id, pdf_text)

            logger.info(f"Successfully added pdf SYNCHRONOUSLY.")
            return jsonify({
                "message": f"Succesfully added pdf",}), 200

        except ValidationError as e:
            logger.error(f"Validation error in add_pdf: {str(e)}")
            return jsonify({"error": f"add_pdf: {str(e)}"}), 400
        except Exception as e:
            logger.exception(f"Unexpected error in add_pdf: {str(e)}")
            return jsonify({"error": f"add_pdf: {str(e)}"}), 500

    # URL/answer_question
    def answer_question(self):
        pass



### Validation helpers
# add pdf validation
def _validate_add_pdf(request):
    try:
        if not "file" in request.files:
            raise ValidationError("No filename provided in file")
        filename = request.files['file'].filename
        if filename == '':
            raise ValidationError("No filename provided in file")
        if not filename.endswith('.pdf'):
            raise ValidationError("File provided is not a pdf")
    except Exception as e:
        raise ValidationError(f"Invalid file format: {e.message}")
