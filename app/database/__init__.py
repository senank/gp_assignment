
# Imports
from typing import Tuple
from psycopg2.extensions import connection, cursor
import psycopg2
import os
import logging
from time import sleep


# Logger
logger = logging.getLogger(__name__)


### DB CONNECTION ###
def connect_to_db() -> Tuple[connection, cursor]:
    """
    Establishes a connection to a PostgreSQL database and returns the connection
    and cursor objects.

    Example:
        >>> conn, cursor = connect_to_db()
        >>> ...
        >>> cur.close()
        >>> conn.close()
    """
    # Database connection details
    logger.info("Attempting to connect to the PostgreSQL database.")
    retries = 5
    while retries > 0:
        try:
            con = psycopg2.connect(
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT")  # Default PostgreSQL port
            )
            logger.info("Successfully connected to the PostgreSQL database.")
            cursor = con.cursor()
            logger.debug("Cursor object created successfully.")
            return con, cursor
        except Exception:
            retries -= 1
            logger.exception("Failed to connect to the PostgreSQL database.")
            sleep(3)
    raise Exception("Error: connect_to_db")
