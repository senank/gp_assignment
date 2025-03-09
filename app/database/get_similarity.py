from ..constants import DB_SECTION, DB_EMBEDDING, DB_TABLE_NAME, DB_TEXT, DB_ID,\
    JSON_TEXT_FILTER
from ..database import connect_to_db

from typing import Tuple, List, Dict
import logging

# Logger
logger = logging.getLogger(__name__)


def get_similarity(emb_text,
                   similarity_limit: float,
                   num_responses: int,
                   filters: Dict) -> List[str]:
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

        # Gets all pdfs with section 0 (initial filtering of documents in the database)
        logger.debug("First stage of retrieval")
        sim_query_high, sim_query_values_high = _get_similarity_query_high_level(
            query_embedding,
            similarity_limit,
            num_responses,
            filters
        )
        cur.execute(sim_query_high, sim_query_values_high)
        top_pdf_ids = cur.fetchall()
        similar_pdf_ids = [row[0] for row in top_pdf_ids]
        logger.debug(f"Successfully retrieved high-level similar pdfs \
                     against embedded text {top_pdf_ids}")

        # Gets all sections related from related pdfs from first query
        logger.debug("Second stage of retrieval")
        sim_query_high, sim_query_values_high = _get_similarity_query_low_level(
            query_embedding,
            similar_pdf_ids,
            similarity_limit,
            num_responses
        )
        cur.execute(sim_query_high, sim_query_values_high)
        similar_chunks = cur.fetchall()
        logger.debug(f"Successfully retrieved low-level similar pdfs from high-level pdfs against embedded text {similar_chunks}")  # noqa: E501
        return similar_chunks

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


def _get_similarity_query_high_level(query_embedding,
                                     similarity_limit,
                                     num_responses,
                                     filters) -> Tuple[str, list]:
    """
    Returns tuple containing a string query and its placeholder values to perform
    high-level similarity search that checks unique pdfs
    """
    logger.info("Building similarity query for text with filters.")
    query = f"""
    SELECT {DB_ID}
    FROM {DB_TABLE_NAME}
    WHERE {DB_SECTION} = 0
    AND 1 - ({DB_EMBEDDING} <=> %s) >= %s
    """
    placeholders=[query_embedding, similarity_limit]
    if filters:
        logger.debug(f"Adding filter {filters} to sql query")
        filter_clauses = []
        for column_name, val in filters.items():
            # Text search filter
            if column_name == JSON_TEXT_FILTER and val not in ["", None]:
                text_filters = []
                for text_val in val:
                    text_filters.append(f"{DB_TEXT} LIKE %s")
                    placeholders.append(f"%{text_val}%")  # Wildcards for partial matching
                    logger.debug(f"Added filter: {DB_TEXT} LIKE '%{text_val}%'")
                text_filters_str = " OR ".join(text_filters)
                logger.info(f"Text filter string = {text_filters_str}")
                filter_clauses.append(f"({text_filters_str})")

            # Can add more filters here

        if filter_clauses:
            query += " AND " + " AND ".join(filter_clauses)
            logger.debug(f"Filter clauses appended to query: \
                         {' AND '.join(filter_clauses)}")

    end_query = f"""
    ORDER BY {DB_EMBEDDING} <=> %s
    LIMIT %s
    """

    placeholders.extend([query_embedding, num_responses])
    query += end_query
    logger.debug(f"Final query: {query}")
    logger.debug(f"Final placeholders: {placeholders}")

    logger.info("Similarity query for text built successfully.")

    return query, placeholders


def _get_similarity_query_low_level(query_embedding,
                                    similar_pdfs: List,
                                    similarity_limit: float,
                                    num_responses: int):
    """
    Returns tuple containing a string query and its placeholder values to perform
    lower-level similarity search that checks section of unique pdf ids in `similar_pdfs`
    """
    query = f"""
    SELECT {DB_ID}, {DB_SECTION}, {DB_TEXT}, 1 - ({DB_EMBEDDING} <=> %s) AS similarity
    FROM {DB_TABLE_NAME}
    WHERE {DB_SECTION} > 0
    AND {DB_ID} = ANY(%s)
    AND 1 - ({DB_EMBEDDING} <=> %s) >= %s
    ORDER BY {DB_EMBEDDING} <=> %s
    LIMIT %s
    """
    placeholders = [query_embedding, similar_pdfs, query_embedding, similarity_limit,
                    query_embedding, num_responses]
    return query, placeholders
