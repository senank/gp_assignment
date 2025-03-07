from ..constants import DB_SECTION, DB_EMBEDDING, DB_TABLE_NAME, DB_TEXT, DB_ID
from ..database import connect_to_db

from typing import Tuple, List
import logging

# Logger
logger = logging.getLogger(__name__)


# TODO: Query for similarity search

def get_similarity(emb_text, similarity_limit: float, num_responses: int) -> List[str]:
    """
    Retrieve similar pdfs based on input

    Example:
        >>> get_similarity([[1, 2...], ...], 5, 0.7)
        [234, 345, 456, 567, 678]
    """
    logger.info(f"Starting similarity search for provided text with \
            similarity limit: {similarity_limit} and max responses: {num_responses}")
    conn, cur = connect_to_db()

    try:
        logger.debug("Using text provided to find similar articles")
        query_embedding = f"{emb_text}"
        
        sim_query, sim_query_values = _get_similarity_query_filter(
            query_embedding,
            similarity_limit,
            num_responses
        )
        cur.execute(sim_query, sim_query_values)
        similar_embeddings = cur.fetchall()
        logger.debug("Successfully retrieved high-level similar pdfs \
                    against embedded text.")



        return similar_embeddings

    except Exception as e:
        conn.rollback()
        logger.exception(f"Error occurred in get_similarity function: {e}")
        raise Exception(f"error: get_similarity: {e}")
    finally:
        if cur:
            cur.close()  # Ensure cursor is closed
            logger.debug("Database cursor closed.")
        if conn:
            conn.close()  # Ensure connection is closed
            logger.debug("Database connection closed.")



def _get_similarity_query_filter(query_embedding,
                          similarity_limit,
                          num_responses) -> Tuple[str, list]:
    """
    Returns tuple containing a string query and its placeholder values to perform
    similarity search using DB_TEXT that contains filters
    """
    logger.info("Building similarity query for text with filters.")
    query = f"""
    SELECT {DB_ID}, {DB_TEXT}, {DB_SECTION}, 1 - ({DB_EMBEDDING} <=> %s) AS similarity
    FROM {DB_TABLE_NAME}
    WHERE {DB_SECTION} = 0
    AND 1 - ({DB_EMBEDDING} <=> %s) >= %s
    ORDER BY {DB_EMBEDDING} <=> %s
    LIMIT %s
    """
    placeholders=[query_embedding, query_embedding, similarity_limit, query_embedding, num_responses]
    logger.debug(f"Final query: {query}")
    logger.debug(f"Final placeholders: {placeholders}")

    logger.info("Similarity query for text built successfully.")

    return query, placeholders
