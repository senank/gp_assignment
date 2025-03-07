from pypdf import PdfReader
from io import BytesIO
import hashlib


def extract_data_from_pdf(pdf_bytes: bytes) -> str:
    """generates a id and extracts the text from a given pdf"""
    hash_obj = hashlib.sha256(pdf_bytes)
    id_ = hash_obj.hexdigest()

    reader = PdfReader(BytesIO(pdf_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""

    return id_, text
