import os

# route.py
MAX_RESPONSES_ID = 5
MAX_RESPONSES = 10
SIMILARITY_LIMIT_ID = 0.5
SIMILARITY_LIMIT = 0.5
BATCH_EXPIRY = 12 * 60 * 60  # 12 hours
CACHE_EXPIRTY = 12 * 60 * 60  # 12 hours


# JSON
JSON_ID = 'rowId'
JSON_QUESTION = 'text'
JSON_SIMILARITY_LIMIT = 'similarity_limit'
JSON_MAX_RESPONSES = 'max_responses'
JSON_BATCH_ID = 'batch_id'


# database.py
DB_TABLE_NAME = 'embeddings'
DB_ID = 'rowid'
DB_TEXT = 'text'
DB_EMBEDDING = 'embedding'
DB_SECTION = 'section'
EXPECTED_SIZE_OF_DB = 5 * 10**6


# embeddings.py
MAX_INPUT_ENC_MODEL = 512
CHUNK_OVERLAP = 100
CHUNK_SIZE = 420
ENCODING_MODEL = os.getenv("ENCODING_MODEL",
                           "multi-qa-mpnet-base-dot-v1")
HUGGING_FACE_KEY = os.getenv("HUGGING_FACE_KEY", "")
HF_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen1.5-7B"

# CORS Validation
ALLOWED_ORIGINS = []
INTERNAL_ORIGINS = [
    "app:5000",
    "192.168.65.1",
    "172.18.0.1",  # github actions ip
]
VALID_API_KEY = "valid"
