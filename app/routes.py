from flask import Blueprint

import logging
logger = logging.getLogger(__name__)


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
        pass

    # URL/answer_question
    def answer_question(self):
        pass