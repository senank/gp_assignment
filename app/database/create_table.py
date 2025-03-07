"""
This module defines all database related functions for interacting with postgreSQL
"""
from psycopg2.extensions import connection, cursor

import logging
from psycopg2 import sql

from ..database import connect_to_db

from ..constants import DB_EMBEDDING, DB_SECTION, DB_TABLE_NAME, DB_TEXT,\
    EXPECTED_SIZE_OF_DB, DB_ID

from math import log, ceil
import re

# Logger
logger = logging.getLogger(__name__)


### TABLE CREATION ###
def create_table(table_name: str) -> None:
    """
    Creates the 'embeddings' table in the PostgreSQL database.

    This function performs the following operations:
    1. Establishes a connection to the PostgreSQL database and creates a cursor object.
    2. Verifies and enables the `pgvector` extension using `check_pgvector()`.
    3a. Creates the 'embeddings' table if it doesn't already exist using
                `make_table_helper()`.
    3b. Validates existing table and vector dimensions
    4. Commits the changes to the database.
    5. Closes the cursor and connection.

    It combines multiple helper functions to ensure that both the required
    extension (`pgvector`) and the table are properly set up for use.


    Example:
        >>> create_table()
        pgvector extension not found. Creating extension...
        Table created successfully, or already exists.
    """
    logger.info(f"Starting the creation of table '{table_name}'.")
    try:
        conn, cur = connect_to_db()
        logger.info("Connected to the PostgreSQL database.")
        # check pgvector is enabled
        logger.debug("Checking if 'pgvector' extension is enabled.")
        _check_pgvector(conn, cur)  # enable pg_vector
        logger.info("'pgvector' extension verified.")

        # Check if table is created
        if not _check_table_exists(conn, cur, table_name):  # Table doesn't exist
            logger.info(f"Table '{table_name}' does not exist. Creating table...")
            _make_table_helper(conn, cur)  # make table from scratch
            logger.info(f"Table '{table_name}' created successfully.")

        else:  # Table exists
            # If vector dimensions mismatch
            if not _validate_vector_dimensions():
                logger.info(
                    f"Table '{table_name}' exists, but vector dimensions mismatched.")
                logger.info("Recreating table to update vector dimensions")
                _drop_embedding_table(conn, cur)
                _make_table_helper(conn, cur)  # make table from scratch
                logger.info(f"Table '{table_name}' created successfully.")

            else:  # Vector dimensions of current table match, update other columns
                logger.info(f"Table '{table_name}' already exists. Validating schema...")
                _validate_table_schema(conn, cur, table_name)  # add/remove columns
                _validate_vector_index()
                logger.info(
                    f"Schema for '{table_name}' validated and updated if necessary.")
        # Commit changes
        conn.commit()
        logger.info(f"Changes committed successfully for table '{table_name}'.")
    except Exception as e:
        logger.exception(f"An error occurred while creating the table '{table_name}'. \
                        Rolling back changes.")
        conn.rollback()
        raise Exception(f"Error: create_table: {e}")
    finally:
        # Close connection
        if cur:
            cur.close()  # Ensure cursor is closed
            logger.debug("Cursor closed successfully.")
        if conn:
            conn.close()  # Ensure connection is closed
            logger.debug("Connection closed successfully.")
        logger.info(f"Finished processing table creation for '{table_name}'.")


def _check_table_exists(conn: connection, cur: cursor, table_name: str) -> bool:
    """
    Checks if table exists in the database

    Example:
        >>> conn, cur = connect_to_db()
        >>> _check_table_exists(conn, cur, 'embeddings')
        True
        >>> _check_table_exists(conn, cur, 'fake_table')
        False
    """
    logger.debug(f"Checking if table '{table_name}' exists.")
    try:
        query = _get_table_exists_query()
        cur.execute(query, (table_name,))
        exists = cur.fetchone()[0]
        if exists:
            logger.info(f"Table '{table_name}' exists.")
        else:
            logger.info(f"Table '{table_name}' does not exist.")
        return exists
    except Exception as e:
        logger.exception(f"Failed to check existence of table '{table_name}'.")
        raise Exception(f"Error: _check_table_exists: {e}")


def _check_pgvector(conn: connection, cur: cursor):
    """
    Checks and enables the pgvector extension in the PostgreSQL database.

    Example:
        >>> conn, cur = connect_to_db()
        >>> check_pgvector(conn, cur)
        pgvector extension not found. Creating extension...
        >>> check_pgvector(conn, cur)
        pgvector extension already installed.
    """
    logger.info("Checking if 'pgvector' extension is installed.")
    try:
        # Check if the pgvector extension is installed
        cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
        if cur.fetchone() is None:
            logger.warning("'pgvector' extension not found. Creating extension...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            logger.info("'pgvector' extension created successfully.")
        else:
            logger.info("'pgvector' extension is already installed.")
    except Exception as e:
        conn.rollback()
        logger.exception("Failed to check or create the 'pgvector' extension.")
        raise Exception(f"Error: check_pgvector: {e}")


def _make_table_helper(conn: connection, cur: cursor):
    """
    Creates the 'embeddings' table in the database if it does not already exist.

    Example:
        >>> conn, cur = connect_to_db()
        >>> make_table_helper(cur)
    """
    logger.info("Creating the table.")
    try:
        # Create table
        create_table_query = _get_create_table_query()
        logger.debug(f"Executing table creation query: {create_table_query}")
        cur.execute(create_table_query)
        # Create table search indexes
        logger.info("Creating indexes for the table.")
        _create_table_index(cur)
        logger.info("Table and indexes created successfully.")
    except Exception as e:
        conn.rollback()
        logger.exception("Failed to create the table.")
        raise Exception(f"Error: make_table_helper: {e}")


def _create_table_index(cur: cursor):
    """
    Creates table indexes by executing SQL queries for index creation.

    Example:
        >>> conn, cur = connect_to_db()
        >>> _create_table_index(cur)
    """
    logger.info("Creating indexes for the table.")
    try:
        create_text_index_query = get_id_index_query()
        logger.debug(f"Executing ID index creation query: {create_text_index_query}")
        cur.execute(create_text_index_query)

        create_vector_index_query = _get_vector_index_query()
        logger.debug(f"Executing vector index creation query: \
                    {create_vector_index_query}")
        cur.execute(create_vector_index_query)

        logger.info("Indexes created successfully.")
    except Exception as e:
        logger.exception("Failed to create indexes for the table.")
        raise Exception(f"Error: _create_table_index: {str(e)}")


# Validation of table
def _validate_table_schema(conn: connection, cur: cursor, table_name: str):
    """
    Validates the schema of a given database table against the expected schema.

    Example:
        >>> conn, cur = connect_to_db()
        >>> _validate_table_schema(conn, cur, "users")
    """
    logger.info(f"Validating schema for table '{table_name}'.")
    try:
        expected_columns_schema = _get_expected_columns_schema()

        query = _get_validation_query()
        logger.debug(f"Executing schema validation query: {query}")
        cur.execute(query, (table_name,))
    except Exception as e:
        logger.exception("Failed during schema validation query execution.")
        raise Exception(f"Error: _validate_table_schema; {e}")

    existing_columns = {row[0]: row[1] for row in cur.fetchall()}
    missing_columns = {col_name: col_type
                       for col_name, col_type in expected_columns_schema.items()
                       if col_name not in existing_columns}
    extra_columns = [col_name for col_name in existing_columns
                     if col_name not in expected_columns_schema]
    logger.debug(f"Existing columns: {existing_columns}")
    logger.debug(f"Missing columns: {missing_columns}")
    logger.debug(f"Extra columns: {extra_columns}")

    try:
        logger.info(f"Adding missing columns: {list(missing_columns.keys())}")
        set_columns(conn, cur, missing_columns, table_name)
        logger.info(f"Removing extra columns: {extra_columns}")
        remove_columns(conn, cur, extra_columns, table_name)
    except Exception as e:
        logger.exception("Failed during schema update.")
        raise Exception(f"Error: _validate_table_schema; {e}")


def _get_expected_columns_schema() -> dict:
    """
    Returns dict containing the expected structure of the db for validation purposes
    """
    return {
        'id': 'integer',
        DB_ID: 'text',
        DB_TEXT: 'character varying',
        DB_EMBEDDING: 'vector',
        DB_SECTION: 'integer'
    }


def _get_validation_query() -> str:
    """ Returns string query to validate the table structure during init' """
    return """
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = %s;
    """


def _validate_vector_dimensions():
    """
    Validates the vector dimensions in the database against the expected dimensions.
    """
    logger.info("Validating vector dimensions in the database.")
    conn, cur = connect_to_db()
    try:
        current_dim = _get_current_vector_dimensions(cur)
        logger.info(f"Current Vector Dimensions: {current_dim}")
    except Exception as e:
        logger.critical(f"Could not get vector dimensions from database: {e}")
        raise Exception(f"Error: validate_vector_dimensions: {e}")
    finally:
        if cur:
            cur.close()  # Ensure cursor is closed
            logger.debug("Cursor closed.")
        if conn:
            conn.close()  # Ensure connection is closed
            logger.debug("Connection closed.")

    vector_type = _get_vector_type()  # Get expected type
    expected_dim = int(vector_type.split("(")[-1].rstrip(")"))  # Extract size
    if current_dim != expected_dim:
        logger.info(f"Vector dimensions mismatched with expected: {expected_dim}")
        return False
    logger.info("Vector dimensions match.")
    return True


def _get_current_vector_dimensions(cur: cursor) -> int:
    """
    Get the current vector dimensions from the database.
    """
    try:
        query = f"""
        SELECT atttypmod
        FROM pg_attribute
        WHERE attrelid='{DB_TABLE_NAME}'::regclass
        AND attname='{DB_EMBEDDING}';
        """
        cur.execute(query)
        result = cur.fetchone()[0]
        return result
    except Exception as e:
        logger.critical(f"Could not get vector dimensions from database: {e}")
        raise Exception(f"Error: _get_current_vector_dimensions: {e}")


def _drop_embedding_table(conn: connection, cur: cursor):
    """
    Drop EMBEDDING_TABLE_NAME table from the database
    """
    try:
        logger.info(f"Dropping table '{DB_TABLE_NAME}'.")
        query = f"DROP TABLE IF EXISTS {DB_TABLE_NAME};"
        cur.execute(query)
        conn.commit()
        logger.info(f"Table '{DB_TABLE_NAME}' dropped successfully.")
    except Exception as e:
        conn.rollback()
        logger.exception(f"Failed to drop table '{DB_TABLE_NAME}'.")
        raise Exception(f"Error: _drop_embedding_table: {e}")



# Setters for Table Columns
def set_columns(conn: connection, cur: cursor, columns_to_add: dict, table_name: str):
    """
    Adds multiple columns to a table if they are missing.

    Iterates over the `columns_to_add` dictionary and calls `set_column` to add each
    missing column to the specified table.

    Parameters:
        conn (connection): A connection object to the database.
        cur (cursor): A cursor object for executing SQL queries.
        columns_to_add (dict): A dictionary where keys are column names and values
                                are their SQL types.
        table_name (str): The name of the table to which columns will be added.
    """
    logger.info(f"Starting to add missing columns to table '{table_name}'.")
    try:
        for col_name, col_type in columns_to_add.items():
            logger.debug(f"Adding column '{col_name}' of type '{col_type}' \
                        to table '{table_name}'.")
            _set_column(col_name, col_type, table_name, conn, cur)
            logger.info(f"Successfully added missing column: {col_name} ({col_type}).")
    except Exception as e:
        logger.exception(f"Failed to add missing columns to table '{table_name}'.")
        raise Exception(f"Error: set_columns; {e}")


def _set_column(col_name: str, col_type: str, table_name: str,
                conn: connection, cur: cursor):
    """
    Adds a single column to the specified table in the database.

    Constructs and executes an SQL query to add the specified column (`col_name`)
    with the given type (`col_type`) to the table.

    Parameters:
        col_name (str): The name of the column to be added.
        col_type (str): The SQL data type of the column.
        table_name (str): The name of the table to which the column will be added.
        conn (connection): A connection object to the database.
        cur (cursor): A cursor object for executing SQL queries.
    """
    logger.debug(f"Preparing to add column '{col_name}' of type '{col_type}' \
                 to table '{table_name}'.")
    try:
        alter_add_column = _get_add_column_query(table_name, col_name, col_type)
        logger.debug(f"Executing query to add column: {alter_add_column}")
        cur.execute(alter_add_column)
        logger.info(f"Column '{col_name}' of type '{col_type}' successfully added \
                    to table '{table_name}'.")
    except Exception as e:
        logger.exception(f"Error occurred while adding column '{col_name}' to table \
                        '{table_name}'.")
        raise Exception(f"Error: set_column; {e}")


def remove_columns(conn: connection, cur: cursor, columns_to_rm: list, table_name: str):
    """
    Removes multiple columns from a table if they exist.

    Iterates over the `columns_to_rm` dictionary and calls `_remove_column` to
    remove any specified column to the specified table.

    Parameters:
        conn (connection): A connection object to the database.
        cur (cursor): A cursor object for executing SQL queries.
        columns_to_rm (dict): A dictionary where keys are column names and
                                values are their SQL types.
        table_name (str): The name of the table to which columns will be added.
    """
    logger.info(f"Starting to remove columns from table '{table_name}'.")
    try:
        for col_name in columns_to_rm:
            logger.debug(f"Attempting to remove column '{col_name}' from table \
                        '{table_name}'.")
            _remove_column(col_name, table_name, conn, cur)
            logger.info(f"Successfully removed column: {col_name}.")
    except Exception as e:
        logger.exception(f"Failed to remove columns from table '{table_name}'.")
        raise Exception(f"Error: remove_columns; {e}")


def _remove_column(col_name: str, table_name: str, conn: connection, cur: cursor):
    """
    Removes a single column from a specified table in the database.

    Constructs and executes an SQL query to remove the specified column (`col_name`)
    from the table.

    Parameters:
        col_name (str): The name of the column to be removed.
        table_name (str): The name of the table to which the column will be removed.
        conn (connection): A connection object to the database.
        cur (cursor): A cursor object for executing SQL queries.
    """
    logger.debug(f"Preparing to remove column '{col_name}' from table '{table_name}'.")
    try:
        alter_rm_column = _get_rm_column_query(table_name, col_name)
        logger.debug(f"Executing query to remove column: {alter_rm_column}")
        cur.execute(alter_rm_column)
        logger.info(f"Column '{col_name}' successfully removed from table \
                    '{table_name}'.")
    except Exception as e:
        logger.exception(f"Error occurred while removing column '{col_name}' \
                        from table '{table_name}'.")
        raise Exception(f"Error: remove_column; {e}")
    

# Validating Vector Index in already created table
def _validate_vector_index():
    """ Validates vector of already created table"""
    logger.info("Validating vector search index")
    index_definition = _get_current_index_settings()
    if index_definition is None:  # index does not exist
        logger.info("Vector search index does not exist, creating")
        _remake_vector_search_index()  # make it
        return
    # else check if they match expected
    logger.debug(f"index_definition: {index_definition}")
    cur_m, cur_ef_con = _extract_index_params(index_definition)
    logger.debug(
        f"current_m: {cur_m}, current_ef_construction: {cur_ef_con}")
    expected_m, expected_ef_con = _get_vector_index_params()
    logger.debug(
        f"expected_m: {expected_m}, expected_ef_construction: {expected_ef_con}")
    if (cur_m != expected_m) or (cur_ef_con != expected_ef_con):
        logger.info("Vector search index does not match, remaking")
        _remake_vector_search_index()
    logger.info("Validated vector search index")


def _get_current_index_settings():
    """ Gets the current embedding search index """
    conn, cur = connect_to_db()
    cur.execute(f"""
        SELECT indexname, indexdef FROM pg_indexes
        WHERE indexname='{DB_EMBEDDING}_search_index';
    """)
    indexes = cur.fetchall()

    for index in indexes:
        if "hnsw" in index[1]:  # Ensure it's an HNSW index
            return index[1]  # Returns the full index definition

    cur.close()
    conn.close()
    return None


def _extract_index_params(index_definition):
    """ Extracts M and ef_construction from the index definition. """
    logger.debug("Using Regex to extract the vector search parameters")
    match = re.search(
        r"WITH \(.*?m\s*=\s*'(\d+)'.*?ef_construction\s*=\s*'(\d+)'.*?\)",
        index_definition,
        re.IGNORECASE)

    if match:
        current_m = int(match.group(1))
        current_ef_con = int(match.group(2))
        return current_m, current_ef_con
    else:
        logger.error("Could not extract vector search parameters")
        return None, None


def _remake_vector_search_index():
    """
    Remaking the vector search index to match m and ef_construction values
    """
    conn, cur = connect_to_db()
    logger.debug("Dropping Vector search index if it exists")
    cur.execute(f"DROP INDEX IF EXISTS {DB_EMBEDDING}_search_index;")

    logger.debug("Creating Vector search index")
    vect_index_query = _get_vector_index_query()
    cur.execute(vect_index_query)
    conn.commit()
    logger.info("Vector search index recreated")
    cur.close()
    conn.close()



### SQL query getters ###
def _get_table_exists_query() -> str:
    """ Returns string query to check if the table is created """
    return """
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = %s
    );
    """


def _get_create_table_query() -> str:
    """ Returns string query to create a table """
    return f"""
    CREATE TABLE IF NOT EXISTS {DB_TABLE_NAME} (
        id SERIAL PRIMARY KEY,
        {DB_ID} VARCHAR(255) NOT NULL,
        {DB_TEXT} TEXT,
        {DB_EMBEDDING} {_get_vector_type()},
        {DB_SECTION} INT
    );
    """


def _get_vector_type() -> str:
    """ Returns the type of vector for pgvector """
    return "vector(1024)"  # Size of mistral-embed encoding model


def get_id_index_query() -> str:
    """ Returns string query to create search index on 'DB_ID' """
    return f"""
    CREATE INDEX IF NOT EXISTS idx_db_id ON {DB_TABLE_NAME} ({DB_ID});
    """


def _get_vector_index_query() -> str:
    """
    Returns string query to create hnsw index on vector 'embedding' using
    cosine similarity
    """
    search_operator = "vector_cosine_ops"

    m, ef_construction = _get_vector_index_params()

    return f"""
    CREATE INDEX IF NOT EXISTS {DB_EMBEDDING}_search_index
    ON {DB_TABLE_NAME} USING hnsw ({DB_EMBEDDING} {search_operator})
    WITH (M={m}, ef_construction={ef_construction});
    """


def _get_vector_index_params():
    """ Gets vector index setting for m and ef_construction"""
    vector_dimension = 1024
    n = EXPECTED_SIZE_OF_DB
    dimensionality = log(n) * (1 + (vector_dimension / 500))

    temp_m = 2 * (dimensionality - 1)
    if temp_m > 64:
        m = 64  # maximum m value in pg_vector
    else:
        m = temp_m

    ef_construction = (2 * m) + (vector_dimension / 10)
    rounded_ef_construction = int(ceil(ef_construction / 100)) * 100

    return m, rounded_ef_construction


def _get_add_column_query(table_name, col_name, col_type) -> str:
    """ Generates an SQL query to add a new column to a table. """
    return sql.SQL("ALTER TABLE {} ADD COLUMN {} {};").format(
        sql.Identifier(table_name),
        sql.Identifier(col_name),
        sql.SQL(col_type)
    )


def _get_rm_column_query(table_name, col_name) -> str:
    """ Generates an SQL query to remove an existing column to a table. """
    return sql.SQL("ALTER TABLE {} DROP COLUMN {};").format(
        sql.Identifier(table_name),
        sql.Identifier(col_name)
    )

