from typing import Dict, List

from .constants import CHUNK_OVERLAP, CHUNK_SIZE, DB_SECTION, DB_EMBEDDING,\
    DB_TEXT, DB_ID
from .embeddings import generate_embedding
from .models import invoke_llm
from .extract_pdf import extract_data_from_pdf

from .database.task_helpers import get_entry_from_db
from .database.add_pdf import add_pdf_to_db
from .database.get_similarity import get_similarity as get_sim

from langchain_text_splitters import RecursiveCharacterTextSplitter

from celery import shared_task
from celery.contrib.abortable import AbortableTask

import logging


logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, base=AbortableTask)
def emb_and_store(self, pdf: bytes) -> Dict:
    """
    Embeds the file data and stores it in the database.

    This function processes the input `pdf` by generating embeddings for the text
    using an encoder model, then stores the processed data in the database.
    """
    try:
        logger.info("Processing pdf")
        pdf_id, pdf_text = extract_data_from_pdf(pdf)

        # Avoid repeat entries
        if get_entry_from_db(pdf_id):
            logger.debug("Found same content in the database,")
            return

        # Entry doesn't exist or has been changed
        logger.info(f"Adding new entry: {pdf_id}")
        data_for_db = _get_data_for_db(pdf_id, pdf_text)

        if data_for_db is None:  # failed/bad vector embedding generation
            logger.error(f"Embedding generation failed for text: {pdf_text}")
            return

        logger.info("Adding processed data to the database.")
        add_pdf_to_db(data_for_db)

        return data_for_db  # returns list of entries added to db

    except Exception as e:
        logger.exception(f"Unexpected error occurred in emb_and_store:task: {e}")
        raise Exception(f"Error occured in emb_and_store: {e}")


def answer_question(question: str,
                    similarity_limit: float,
                    max_responses: int,
                    filters: Dict) -> str:
    """
    Perform similarity comparison based on provided text, then answers the question in
    the text.
    """
    try:
        logger.info("Calculating embedding for provided text.")
        emb_text = generate_embedding([question])[0]

        logger.debug("Getting sources for answer")
        answer_sources = get_sim(emb_text, similarity_limit, max_responses, filters)
        logger
        logger.debug(f"Sources for answer: {answer_sources}")
        logger.debug(f"Invoking LLM with {question} and sources")

        # Remove id, section and similarity score from the sources for llm
        answer = invoke_llm(question, [fact[2] for fact in answer_sources])
        if not answer:
            logger.debug(f"Invoking LLM returned empty str: {answer}")
            raise Exception("task: answer_question could not generate answer")
        return answer

    except Exception as e:
        logger.exception(f"Unexpected error occurred in get_similarity:task: {e}")
        raise Exception(f"Error occured in emb_and_store: {e}")


def _get_data_for_db(id_: str, content: str) -> List[Dict]:
    """
    Converts the pdf data into chunked sections that are embedded to be stored in the db
    """
    text_to_embed = []
    data_for_db = []

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE,
                                              chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.split_text(content)  # split content

    text_to_embed.append(content)  # Store full content at index 0
    for chunk in chunks:
        text_to_embed.append(chunk)

    emb_inputs = generate_embedding(text_to_embed)

    # Make list of dictionaries to pass to add_pdf
    for i, emb_input in enumerate(emb_inputs):
        logger.debug(f"Processing chunk {i + 1}/{len(chunks)}")
        pdf_chunk = {}  # Make copy of the main entry
        pdf_chunk[DB_ID] = id_
        pdf_chunk[DB_TEXT] = text_to_embed[i]  # Replace text with chunk of text
        pdf_chunk[DB_EMBEDDING] = emb_input
        pdf_chunk[DB_SECTION] = i
        data_for_db.append(pdf_chunk)

    return data_for_db
