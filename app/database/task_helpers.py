from ..database import connect_to_db
from ..constants import DB_TABLE_NAME, DB_ID, DB_SECTION

import logging


# Logger
logger = logging.getLogger(__name__)


# Task Helpers
def get_entry_from_db(id_: str):
    """
    Checks if an entry with the specified `content` in the text column of the db exists.

    Example:
        # DB contains rowId: '1', but not rowId: '2'
        >>> get_entry_from_db('1')
        True
        >>> get_entry_from_db('2')
        False
    """
    conn, cur = connect_to_db()
    try:
        query = f"""SELECT EXISTS(
            SELECT 1 FROM {DB_TABLE_NAME}
            WHERE {DB_ID} = %s
            );
            """
        cur.execute(query, (id_,))
        result = bool(cur.fetchone()[0])
    except Exception as e:
        logger.error(f"Error in get_entry_from_db with id {id_}: {e}")
        result = False
    finally:
        cur.close()
        conn.close()
        return result
