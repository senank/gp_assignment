"""
This module provides utilities for generating, processing, and managing text embeddings
"""
# Imports
import numpy as np

import math

from typing import List

from .constants import ENCODING_MODEL, MISTRAL_API_KEY
from mistralai import Mistral

import logging
logger = logging.getLogger(__name__)


# embeddings
def generate_embedding(text_inputs: List[str]) -> list[float]:
    """
    Generates embeddings for a given parsed input.
    """
    logger.info(f"Starting embedding generation for {len(text_inputs)} chunks using \
                model {ENCODING_MODEL}.")
    try:
        client = Mistral(api_key=MISTRAL_API_KEY)
        logger.debug("Sending text to embeddings endpoint.")
        embeddings = client.embeddings.create(
            model = ENCODING_MODEL,
            inputs=text_inputs
        )
        embedded_texts = [embeddings.data[i].embedding for i in range(0,len(text_inputs))]
        logger.debug(f"Received {len(embedded_texts)} embeddings from OpenAI.")
        return embedded_texts
    except Exception as e:
        logger.exception(f"An error occurred during embedding generation: {e}")
        return []
