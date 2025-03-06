from ..constants import DB_SECTION, DB_EMBEDDING, DB_EMBEDDING_TABLE_NAME, DB_ID, DB_DATE, JSON_DATE_FROM, JSON_DATE_TO
from ..database import connect_to_db

from typing import Tuple, List
import logging

# Logger
logger = logging.getLogger(__name__)


# TODO Query for similarity search

def get_similarity(emb_text, num_responses: int, similarity_limit: float) -> List[str]:
    """
    Retrieve similar pdfs based on input

    """
    pass
