from typing import List
from ..database import connect_to_db

import psycopg2

from ..constants import DB_TABLE_NAME, DB_ID

import logging

# Logger
logger = logging.getLogger(__name__)


def add_pdf_to_db(data: List[dict]) -> None:
    """
    Inserts pdf data into the table in the database.

    Example:
        >>> data = {'title': 'pdf 1', 'vector': [0.1, 0.2, 0.3]}
        >>> add_pdf_to_db(data)
    """
    logger.info("Starting to add pdf to the database.")
    conn, cur = connect_to_db()
    for pdf in data:
        try:
            logger.debug("Preparing to insert pdf to db")
            query = _get_add_pdf_query(pdf)
            cur.execute(query, list(pdf.values()))
            conn.commit()
            logger.info(f"Successfully inserted pdf: {pdf[DB_ID]}")
        except Exception as e:
            conn.rollback()
            logger.exception(f"Failed to insert pdf: {pdf}.\
                             Rolling back transaction.: {e}")
    if cur:
        cur.close()  # Ensure cursor is closed
        logger.debug("Cursor closed.")
    if conn:
        conn.close()  # Ensure connection is closed
        logger.debug("Connection closed.")
    logger.info("Finished adding pdf(s) to the database.")



def _get_add_pdf_query(data: dict) -> str:
    """ Returns string query to add pdf based on data to database """
    # Prepare column names and values
    columns = ', '.join([key.lower() for key in data.keys()])
    placeholders = ', '.join(['%s'] * len(data))
    # Create the SQL query
    return f"INSERT INTO {DB_TABLE_NAME} ({columns}) VALUES ({placeholders})"