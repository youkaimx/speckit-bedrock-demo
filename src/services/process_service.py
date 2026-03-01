"""Processing pipeline: extract text → chunk → embed → store in S3 Vectors → update status → schedule S3 delete."""

from datetime import UTC, datetime

from src.models.document import DocumentFormat, ProcessingStatus
from src.services import embedding_service, extract_service
from src.storage import metadata as metadata_store
from src.storage import s3 as s3_storage
from src.storage import vectors as vectors_storage

# Chunk size for embedding (Titan accepts up to 8192 tokens; ~4000 chars is safe per chunk).
CHUNK_SIZE = 4000
CHUNK_OVERLAP = 200


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    if not text or not text.strip():
        return []
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - CHUNK_OVERLAP if end < len(text) else len(text)
    return chunks


def process_document(owner_id: str, filename: str) -> None:
    """
    Run the full pipeline for one document: read from S3, extract text, chunk, embed, store vectors,
    update metadata to processed, then delete the S3 object (schedule for deletion per FR-005).
    On any failure: set status to failed, set processing_error, do not store partial embeddings,
    do not delete S3 object (T031).
    """
    doc = metadata_store.get_metadata(owner_id, filename)
    if not doc:
        _set_failed(owner_id, filename, "Document not found in metadata")
        return
    if doc.processing_status == ProcessingStatus.PROCESSED:
        return
    metadata_store.update_status(
        owner_id, filename, ProcessingStatus.PROCESSING, clear_processing_error=True
    )
    try:
        content = s3_storage.get_document(owner_id, filename)
        if not content:
            _set_failed(owner_id, filename, "Document not found in S3")
            return
        text = extract_service.extract_text(content, DocumentFormat(doc.format))
        chunks = _chunk_text(text)
        if not chunks:
            _set_failed(owner_id, filename, "No text extracted from document")
            return
        vectors_with_text: list[tuple[list[float], str]] = []
        for chunk in chunks:
            emb = embedding_service.embed_text(chunk)
            vectors_with_text.append((emb, chunk))
        vectors_storage.store_vectors(owner_id, filename, vectors_with_text)
        now = datetime.now(UTC)
        metadata_store.update_status(
            owner_id,
            filename,
            ProcessingStatus.PROCESSED,
            processed_at=now,
            clear_processing_error=True,
        )
        s3_storage.delete_document(owner_id, filename)
    except Exception as e:
        _set_failed(owner_id, filename, str(e))
        raise


def _set_failed(owner_id: str, filename: str, message: str) -> None:
    """Set document status to failed with error message; do not store partial embeddings or delete S3."""
    metadata_store.update_status(
        owner_id,
        filename,
        ProcessingStatus.FAILED,
        processing_error=message,
    )
