from PyPDF2 import PdfReader

from .extensions import vectorizer, embeddings_store
from . import extensions as ext
from .models import Chunk


def extract_text_from_pdf(file_stream) -> str:
    """Extract plain text from a PDF file object."""
    reader = PdfReader(file_stream)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text += page_text + "\n"
    return text


def chunk_text(text: str, max_chars: int = 1000):
    """Split long text into fixed-size chunks."""
    chunks = []
    text = text.strip()
    for i in range(0, len(text), max_chars):
        chunk = text[i:i + max_chars]
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def simple_summary(text: str, max_chars: int = 500) -> str:
    """Very simple summary: first few lines up to max_chars."""
    text = text.strip()
    if not text:
        return ""
    lines = text.splitlines()
    summary = "\n".join(lines[:5])
    if len(summary) > max_chars:
        summary = summary[:max_chars] + "..."
    return summary


def rebuild_vector_store_from_db():
    """
    Load all chunks from DB and rebuild TF-IDF matrix.
    """
    from .models import Chunk  # local import to avoid circulars

    # reset store
    embeddings_store.clear()

    all_chunks = Chunk.query.all()
    for c in all_chunks:
        embeddings_store.append({
            "record_id": c.record_id,
            "chunk_text": c.chunk_text
        })

    if not embeddings_store:
        ext.chunk_vectors = None
        return

    texts = [item["chunk_text"] for item in embeddings_store]
    ext.chunk_vectors = vectorizer.fit_transform(texts)
