from typing import List
from ..database import connect_to_db

import psycopg2

from ..constants import JSON_ID, DB_EMBEDDING_TABLE_NAME

import logging

# Logger
logger = logging.getLogger(__name__)


def add_pdf_to_db(data: List[dict]) -> None:
    """
    Inserts pdf data into the table in the database.

    """
    pass