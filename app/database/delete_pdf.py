import logging

from ..database import connect_to_db
from ..constants import DB_TABLE_NAME, DB_ID, DB_EMBEDDING

logger = logging.getLogger(__name__)

def delete_pdf_id(id_: str) -> None:
    """
    Deletes the specified ID from the database.
    """
    logger.info(f"Attempting to delete entry with ID: {id_}")
    conn, cur = connect_to_db()
    try:
        # Retrieve the embedding for the given DB_ID
        logger.debug(f"Fetching existing entry for deletion with ID: {id_}")
        embedding_query = _get_delete_exists_query()
        cur.execute(embedding_query, (id_,))
        result = cur.fetchone()
        if not result:
            logger.info(f"No entry found for DB_ID: {id_}")
            raise ValueError(f"No entry found for {DB_ID}: {id_}")

        delete_query = _get_delete_pdf_query()
        logger.debug(f"Executing delete query for ID: {id_}")
        cur.execute(delete_query, (id_,))
        conn.commit()
        logger.info(f"Successfully deleted entry with ID: {id_}")

    except Exception as e:
        conn.rollback()
        logger.exception(f"delete_id_from_db: Error occurred during deletion process: \
                         {e}")
        raise Exception(f"delete_id:database: {e}")
    finally:
        if cur:
            cur.close()  # Ensure cursor is closed
            logger.debug("Database cursor closed.")
        if conn:
            conn.close()  # Ensure connection is closed
            logger.debug("Database connection closed.")


def _get_delete_pdf_query() -> str:
    """ Returns string query to hard delete all entries with a given DB_ID exists """
    return f"DELETE FROM {DB_TABLE_NAME} WHERE {DB_ID} = %s;"


def _get_delete_exists_query() -> str:
    """ Returns string query to check if entry exists """
    return f"""
    SELECT {DB_EMBEDDING}
    FROM {DB_TABLE_NAME}
    WHERE {DB_ID} = %s;
    """
