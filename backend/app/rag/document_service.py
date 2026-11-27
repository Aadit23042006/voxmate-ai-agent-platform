"""Minimal RAG (Retrieval-Augmented Generation) service.

Ingest: chunk a document's text -> embed each chunk (Gemini embeddings,
falling back to no vector in mock mode) -> store as DocumentChunk rows.

Retrieve: embed the query -> cosine-similarity rank all of the user's
chunks in Python -> return the top-k. This is intentionally simple
(no pgvector/FAISS) — fine up to a few thousand chunks per user, which
covers a portfolio demo; swap in a real vector index if this needs to
scale further.
"""
import math

from app.agents.llm_client import embed_text
from app.models.models import Document, DocumentChunk

CHUNK_SIZE_CHARS = 1200
CHUNK_OVERLAP_CHARS = 150
TOP_K = 4


def chunk_text(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE_CHARS, len(text))
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = end - CHUNK_OVERLAP_CHARS
    return [c for c in chunks if c]


def ingest_document(db, user, filename: str, mime_type: str, text: str) -> Document:
    document = Document(user_id=user.id, filename=filename, mime_type=mime_type)
    db.add(document)
    db.flush()  # get document.id before creating chunks

    for i, chunk in enumerate(chunk_text(text)):
        embedding = embed_text(chunk)
        db.add(DocumentChunk(
            document_id=document.id, user_id=user.id,
            chunk_index=i, content=chunk, embedding=embedding,
        ))

    db.commit()
    db.refresh(document)
    return document


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity only for valid, compatible vectors."""
    if not isinstance(a, (list, tuple)) or not isinstance(b, (list, tuple)):
        return 0.0

    if not a or not b or len(a) != len(b):
        return 0.0

    try:
        a_values = [float(x) for x in a]
        b_values = [float(x) for x in b]

        if not all(math.isfinite(x) for x in a_values + b_values):
            return 0.0

        dot = sum(x * y for x, y in zip(a_values, b_values))
        norm_a = math.sqrt(sum(x * x for x in a_values))
        norm_b = math.sqrt(sum(y * y for y in b_values))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    except (TypeError, ValueError, OverflowError):
        return 0.0


def retrieve_relevant_chunks(db, user, query: str, k: int = TOP_K) -> list[DocumentChunk]:
    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.user_id == user.id
    ).all()

    if not chunks or k <= 0:
        return []

    # Use keyword retrieval if embedding generation is unavailable.
    try:
        query_embedding = embed_text(query)
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "Query embedding failed; using keyword retrieval",
            exc_info=True,
        )
        query_embedding = None

    valid_query = (
        isinstance(query_embedding, (list, tuple))
        and len(query_embedding) > 0
    )

    if valid_query:
        try:
            valid_query = all(
                math.isfinite(float(value))
                for value in query_embedding
            )
        except (TypeError, ValueError, OverflowError):
            valid_query = False

    # Ignore missing, malformed, and dimension-incompatible stored vectors.
    compatible_chunks = []

    if valid_query:
        for chunk in chunks:
            vector = chunk.embedding

            if not isinstance(vector, (list, tuple)):
                continue

            if len(vector) != len(query_embedding):
                continue

            similarity = _cosine_similarity(query_embedding, vector)
            compatible_chunks.append((similarity, chunk))

    if compatible_chunks:
        compatible_chunks.sort(key=lambda pair: pair[0], reverse=True)
        return [chunk for _, chunk in compatible_chunks[:k]]

    # No usable embeddings: fall back to keyword-overlap ranking.
    query_words = set(query.lower().split())
    scored = []

    for chunk in chunks:
        overlap = len(
            query_words & set(chunk.content.lower().split())
        )
        scored.append((overlap, chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [chunk for _, chunk in scored[:k]]
