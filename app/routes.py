from flask import request, jsonify, Blueprint, current_app
from jsonschema import validate, ValidationError
import json

from time import time

import redis

from .constants import JSON_QUESTION, SIMILARITY_LIMIT, MAX_RESPONSES,\
    JSON_SIMILARITY_LIMIT, JSON_MAX_RESPONSES, CACHE_EXPIRY, JSON_FILTERS,\
    JSON_TEXT_FILTER

from .task import emb_and_store, answer_question
from .redis_cache import cache_key_answer_question, set_cache, get_cache

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
        overall_start = time()
        logger.info("Processing add_pdf request.")
        try:
            # Validate request is a pdf file
            _validate_add_pdf(request)
            logger.debug("Validated file data type")

            # Get bytes from file
            pdf = request.files['file'].read()
            logger.debug("Extracted file bytes")

            # Checking if redis and celery worker available
            service_start = time()
            logger.debug("Checking if redis are available")
            _redis_healthcheck()  # Healthcheck redis for .delay
            logger.debug("Checking if celery workers are available")
            _is_celery_worker_active()  # Check if celery worker is active
            service_time = time() - service_start

            logger.debug("Adding pdf to the db asynchronously.")
            emb_and_store.delay(pdf)

            logger.info("Successfully added pdf ASYNCHRONOUSLY")
            overall_time = time() - overall_start
            return jsonify({
                "message": "Succesfully added pdf",
                "latency": {
                    "overall_time": overall_time,
                    "service_check_time": service_time
                }
            }), 200
        except ConnectionError:
            service_time = time() - service_start
            logger.error("Connection error to redis/celery.")
            logger.debug("Adding pdf to the db synchronously.")
            emb_and_store(pdf)

            logger.info("Successfully added pdf SYNCHRONOUSLY.")
            overall_time = time() - overall_start
            return jsonify({
                "message": "Succesfully added pdf",
                "latency": {
                    "overall_time": overall_time,
                    "service_check_time": service_time
                }
            }), 200

        except ValidationError as e:
            logger.error(f"Validation error in add_pdf: {str(e)}")
            return jsonify({"error": f"add_pdf: {str(e)}"}), 400
        except Exception as e:
            logger.exception(f"Unexpected error in add_pdf: {str(e)}")
            return jsonify({"error": f"add_pdf: {str(e)}"}), 500

    # URL/answer_question
    def answer_question(self):
        """
        Handles /answer_question POST requests to answer a question.

        1) Takes a text input (question) and text_filters (filters)
        2) Checks Cache for recent response
        3a) If cached
            - returns cached data as response
        3b) If not cached
            - embeds text_input
            - queries db using cosine search with text_filters if applicable
            - invokes llm with question and sources returned from db query
            - caches result
            - returns result
        """
        logger.info("Processing compare_text request.")
        overall_start = time()
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
                overall_time = time() - overall_start
                return jsonify({
                    'message': 'need a valid question query',
                    'data': "",
                    "latency": {
                        "overall_time": overall_time
                    }}), 404

            similarity_limit = data.get(JSON_SIMILARITY_LIMIT, SIMILARITY_LIMIT)
            max_responses = data.get(JSON_MAX_RESPONSES, MAX_RESPONSES)
            filters = data.get(JSON_FILTERS, {})
            
            service_start = time()
            _redis_healthcheck()  # Healthcheck redis cache
            service_time = time() - service_start

            redis_client = current_app.config["REDIS_CACHE"]

            logger.debug("Checking cache for similarity comparison.")
            cached_similarity_key = cache_key_answer_question(question_text, filters)
            status, cached_result = get_cache(redis_client, cached_similarity_key)
            if status == 1:  # if cached
                logger.info("Found similarity comparison data for text input in cache.")
                overall_time = time() - overall_start
                return jsonify({
                    'message': 'Found search in Cache',
                    'data': json.loads(cached_result),
                    'latency': {
                        "overall_time": overall_time,
                        "service_check_time": service_time
                    }}), 200

            # If not cached
            logger.info("No similarity comparison data for text input in cache; \
                        querying db")
            answer, db_query_time, invoke_time = answer_question(
                question_text,
                similarity_limit,
                max_responses,
                filters
            )

            logger.info("Setting cache for similarity comparison based on text")
            set_cache(redis_client, cached_similarity_key, json.dumps(answer),
                      ex=CACHE_EXPIRY)

            logger.info("Successfully generated answer to given question")
            overall_time = time() - overall_start
            return jsonify({
                'message': f"Successfully generated answer to {question_text}",
                'data': answer,
                "latency": {
                    "overall_time": overall_time,
                    "service_check_time": service_time,
                    "db_query_time": db_query_time,
                    "model_invocation_time": invoke_time
                }}), 200

        except ConnectionError:
            logger.error("Connection error to redis, not checking cache")
            service_time = time() - service_start

            answer, db_query_time, invoke_time = answer_question(
                question_text,
                similarity_limit,
                max_responses,
                filters
            )

            logger.info("Successfully generated similar IDs, with filters, to \
                        the given input text")
            overall_time = time() - overall_start
            return jsonify({
                'message': f"Successfully generated answer to {question_text}",
                'data': answer,
                "latency": {
                    "overall_time": overall_time,
                    "service_check_time": service_time,
                    "db_query_time": db_query_time,
                    "model_invocation_time": invoke_time
                }}), 200

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
            JSON_MAX_RESPONSES: {"type": "integer"},
            JSON_FILTERS: {
                "type": "object",
                "properties": {
                    JSON_TEXT_FILTER: {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                }
            }
        },
        "required": [JSON_QUESTION],
        "additionalProperties": False
    }
