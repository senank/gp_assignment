from flask import request, jsonify, Blueprint, current_app
from jsonschema import validate, ValidationError
import json

import redis

from .constants import JSON_QUESTION, SIMILARITY_LIMIT, MAX_RESPONSES,\
    JSON_SIMILARITY_LIMIT, JSON_MAX_RESPONSES, CACHE_EXPIRY

from .task import emb_and_store, answer_question
from .redis_cache import cache_key_answer_question, set_cache, get_cache
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

        self.api_routes_bp.add_url_rule('/', 'home', self.home,
                                        methods=['GET'])

        self.api_routes_bp.add_url_rule('/add_pdf', 'add_pdf', self.add_pdf,
                                        methods=['POST'])

        self.api_routes_bp.add_url_rule('/answer_question', 'answer_question',
                                        self.answer_question, methods=['POST'])

        logger.debug("Successfully registered routes")

    # URL/
    def home(self):
        """ Default GET url to test if app is working """
        return "working"

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

            logger.info("Successfully added pdf ASYNCHRONOUSLY")
            return jsonify({"message": "Succesfully added pdf"}), 200
        except ConnectionError:
            logger.error("Connection error to redis, adding synchronously")
            logger.debug(f"Adding {pdf_text} to the db.")
            emb_and_store(pdf_id, pdf_text)

            logger.info("Successfully added pdf SYNCHRONOUSLY.")
            return jsonify({
                "message": "Succesfully added pdf",}), 200

        except ValidationError as e:
            logger.error(f"Validation error in add_pdf: {str(e)}")
            return jsonify({"error": f"add_pdf: {str(e)}"}), 400
        except Exception as e:
            logger.exception(f"Unexpected error in add_pdf: {str(e)}")
            return jsonify({"error": f"add_pdf: {str(e)}"}), 500

    # URL/answer_question
    def answer_question(self):
        logger.info("Processing compare_text request.")
        try:
            if not request.is_json:
                logger.error("Request content is not JSON.")
                return jsonify({"error": "Request content is not JSON"}), 400

            # Get json data
            data = request.get_json()
            logger.debug("Received JSON data")
            _validate_answer_question(data)
            logger.debug("Validated JSON data")

            question_text = data[JSON_QUESTION]
            if not question_text:
                return jsonify({
                    'message': 'need a valid question query',
                    'data': ""}), 404

            similarity_limit = data.get(JSON_SIMILARITY_LIMIT, SIMILARITY_LIMIT)
            max_responses = data.get(JSON_MAX_RESPONSES, MAX_RESPONSES)

            _redis_healthcheck()  # Healthcheck redis cache

            redis_client = current_app.config["REDIS_CACHE"]

            logger.debug("Checking cache for similarity comparison.")
            cached_similarity_key = cache_key_answer_question(question_text)
            status, cached_result = get_cache(redis_client, cached_similarity_key)
            if status == 1:  # if cached
                logger.info("Found similarity comparison data for text input in cache.")
                return jsonify({
                    'message': 'Found search in Cache',
                    'data': json.loads(cached_result)}), 200

            # If not cached
            logger.info("No similarity comparison data for text input in cache; \
                        querying db")
            answer = answer_question(question_text, similarity_limit, max_responses)

            logger.info("Setting cache for similarity comparison based on text")
            set_cache(redis_client, cached_similarity_key, json.dumps(answer),
                      ex=CACHE_EXPIRY)

            logger.info("Successfully generated answer to given question")
            return jsonify({
                'message': f"Successfully generated answer to {question_text}",
                'data': answer}), 200

        except ConnectionError:
            logger.error("Connection error to redis, not checking cache")

            answer = answer_question(question_text, similarity_limit, max_responses)

            logger.info("Successfully generated similar IDs, with filters, to \
                        the given input text")
            return jsonify({
                'message': f"Successfully generated answer to {question_text}",
                'data': answer}), 200

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return jsonify({"error": f"compare_text: {str(e)}"}), 400
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
            return jsonify({"error": f"compare_text: {str(e)}"}), 500


### Validation helpers
# add pdf validation
def _validate_add_pdf(request):
    try:
        if "file" not in request.files:
            raise ValidationError("No filename provided in file")
        filename = request.files['file'].filename
        if filename == '':
            raise ValidationError("No filename provided in file")
        if not filename.endswith('.pdf'):
            raise ValidationError("File provided is not a pdf")
    except Exception as e:
        raise ValidationError(f"Invalid file format: {e.message}")


# answer_question validation
def _validate_answer_question(data):
    try:
        data = request.get_json()
        validate(instance=data, schema=_get_json_schema_answer_text())
    except ValidationError as e:
        raise ValidationError(f"Invalid JSON format: {e.message}")


# compare_text schema
def _get_json_schema_answer_text():
    return {
        "type": "object",
        "properties": {
            JSON_QUESTION: {"type": "string"},
            JSON_SIMILARITY_LIMIT: {"type": "number"},
            JSON_MAX_RESPONSES: {"type": "integer"}
        },
        "required": [JSON_QUESTION],
        "additionalProperties": False
    }
