"""
This module provides utilities for generating, processing, and managing text embeddings
"""
# Imports
from typing import List

from .constants import MISTRAL_ENCODING_MODEL, MISTRAL_API_KEY, ST_ENCODING_MODEL
from mistralai import Mistral

from numpy import linalg

from sentence_transformers import SentenceTransformer

import logging
logger = logging.getLogger(__name__)


# TODO Swap mistral for in-memory as per instructions

# embeddings
def generate_embedding_mistral(text_inputs: List[str]) -> List[List[float]]:
    """
    Generates embeddings for a given parsed input.
    """
    logger.info(f"Starting embedding generation for {len(text_inputs)} chunks using \
                model {MISTRAL_ENCODING_MODEL}.")
    try:
        client = Mistral(api_key=MISTRAL_API_KEY)
        logger.debug("Sending text to embeddings endpoint.")
        embeddings = client.embeddings.create(
            model=MISTRAL_ENCODING_MODEL,
            inputs=text_inputs
        )
        embedded_texts = [embeddings.data[i].embedding for i in range(0,len(text_inputs))]
        logger.debug(f"Received {len(embedded_texts)} embeddings from OpenAI.")
        return embedded_texts
    except Exception as e:
        logger.exception(f"An error occurred during embedding generation: {e}")
        return []


model = SentenceTransformer('all-MiniLM-L6-v2')

# embeddings
def generate_embedding(text_inputs: List[str]) -> List[List[float]]:
    """
    Generates embeddings for a given parsed input.
    """
    logger.info(f"Starting embedding generation for {len(text_inputs)} chunks using \
                sentenceTransformer model: {ST_ENCODING_MODEL}.")
    try:
        embeddings = model.encode(text_inputs, convert_to_numpy=True)
        # Normalizing to improve cosine similarity performace
        normalized_embeddings = embeddings / linalg.norm(embeddings, axis=1, keepdims=True)
        embedded_texts = [embedding.tolist() for embedding in normalized_embeddings]
        logger.debug(
            f"Received {len(embedded_texts)} embeddings with \
            {len(embedded_texts[0])} dimensions from SentenceTransfomer."
        )
        return embedded_texts
    except Exception as e:
        logger.exception(f"An error occurred during embedding generation: {e}")
        return []
