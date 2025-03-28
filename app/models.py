import logging
from typing import List

from mistralai import Mistral

from .constants import MISTRAL_API_KEY

logger = logging.getLogger(__name__)


def invoke_llm(question: str, content: List[str]):
    """
    Send a given prompt to an open-source llm on mistral
    """
    if not content:
        return f"There are not facts available that are related to {question}"
    try:
        client = Mistral(api_key=MISTRAL_API_KEY)
        chat_response = client.chat.complete(
            model=_get_model(),
            messages=[
                {
                    "role": "user",
                    "content": rag_prompt.format(question=question, content=content),
                },
            ]
        )
        return chat_response.choices[0].message.content
    except Exception as e:
        logger.error(f"invoking mistral face llm: {e}")


def _get_model():
    return "mistral-small-latest"


rag_prompt = """
Generate an answer the the question in the <question> XML tag exclusively using the provided facts in the <facts> XML tag

### **Question**
<question>{question}</question>

### **Article to Analyze**
<facts>{content}</facts>
"""  # noqa: E501
