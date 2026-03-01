"""Retrieval from S3 Vectors: query by embedding, filter by owner_id. Returns chunks with text and document filename."""

from src.storage import vectors as vectors_storage

# Default number of chunks to retrieve for RAG context.
DEFAULT_TOP_K = 10


def retrieve(
    owner_id: str,
    query_embedding: list[float],
    top_k: int = DEFAULT_TOP_K,
) -> list[tuple[str, str]]:
    """
    Query S3 Vectors for nearest neighbors to query_embedding, scoped to owner_id.
    Returns list of (chunk_text, document_filename) for building RAG context.
    """
    return vectors_storage.query_vectors(owner_id, query_embedding, top_k=top_k)
