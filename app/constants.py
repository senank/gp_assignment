import os

# route.py
MAX_RESPONSES = 10
SIMILARITY_LIMIT = 0.6
CACHE_EXPIRY = 12 * 60 * 60  # 12 hours


# JSON
JSON_QUESTION = 'text'
JSON_SIMILARITY_LIMIT = 'similarity_limit'
JSON_MAX_RESPONSES = 'max_responses'


# database.py
DB_TABLE_NAME = 'embeddings'
DB_ID = 'row_id'
DB_TEXT = 'text'
DB_EMBEDDING = 'embedding'
DB_SECTION = 'section'
EXPECTED_SIZE_OF_DB = 5 * 10**6


# embeddings.py
CHUNK_OVERLAP = 200
CHUNK_SIZE = 800
MISTRAL_ENCODING_MODEL = "mistral-embed"
ST_ENCODING_MODEL = 'all-MiniLM-L6-v2'
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")

# CORS Validation
ALLOWED_ORIGINS = []
INTERNAL_ORIGINS = [
    "app:5000",
    "192.168.65.1",
    "172.18.0.1",  # github actions ip
]
VALID_API_KEY = "valid"
