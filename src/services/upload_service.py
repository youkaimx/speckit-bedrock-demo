"""Upload service: validate 25 MB max, PDF/Markdown only, replace-on-same-filename."""

from datetime import UTC, datetime
from typing import BinaryIO

from src.models.document import Document, DocumentFormat, ProcessingStatus
from src.storage import metadata as metadata_store
from src.storage import s3 as s3_storage
from src.storage import vectors as vectors_storage

MAX_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_CONTENT_TYPES = {
    "application/pdf": DocumentFormat.PDF,
    "text/markdown": DocumentFormat.MARKDOWN,
    "text/x-markdown": DocumentFormat.MARKDOWN,
}
ALLOWED_EXTENSIONS = {
    ".pdf": DocumentFormat.PDF,
    ".md": DocumentFormat.MARKDOWN,
    ".markdown": DocumentFormat.MARKDOWN,
}


def _infer_format(filename: str, content_type: str | None) -> DocumentFormat | None:
    fmt = None
    if content_type and content_type.split(";")[0].strip().lower() in ALLOWED_CONTENT_TYPES:
        fmt = ALLOWED_CONTENT_TYPES[content_type.split(";")[0].strip().lower()]
    if fmt is None and filename:
        import os

        ext = os.path.splitext(filename)[1].lower()
        fmt = ALLOWED_EXTENSIONS.get(ext)
    return fmt


def validate_upload(
    filename: str,
    content_type: str | None,
    size: int,
) -> tuple[DocumentFormat | None, str | None]:
    """
    Validate file: format (PDF/Markdown only), size (max 25 MB).
    Returns (format, error_message). format is None if invalid.
    """
    if not filename or not filename.strip():
        return None, "Missing or invalid filename"
    if size <= 0:
        return None, "Empty file"
    if size > MAX_SIZE_BYTES:
        return None, f"File exceeds 25 MB limit ({size} bytes)"
    fmt = _infer_format(filename, content_type)
    if fmt is None:
        return None, "Invalid format: only PDF and Markdown are allowed"
    return fmt, None


def upload_document(
    owner_id: str,
    filename: str,
    body: BinaryIO,
    content_type: str | None,
    size: int,
    mode: str,
) -> Document:
    """
    Upload document: validate, store in S3, create/update metadata.
    Replace-on-same-filename: overwrite S3 and metadata.
    Returns Document. processing_status is 'processing' for upload_and_analyze, 'pending' for upload_and_queue.
    """
    fmt, err = validate_upload(filename, content_type, size)
    if err:
        raise ValueError(err)
    now = datetime.now(UTC)
    status = (
        ProcessingStatus.PROCESSING if mode == "upload_and_analyze" else ProcessingStatus.PENDING
    )
    ct = content_type or ("application/pdf" if fmt == DocumentFormat.PDF else "text/markdown")
    s3_storage.upload_document(owner_id, filename, body, ct)
    doc = Document(
        filename=filename,
        owner_id=owner_id,
        format=fmt,
        size_bytes=size,
        uploaded_at=now,
        processing_status=status,
        processing_error=None,
        processed_at=None,
    )
    metadata_store.create_metadata(doc)
    return doc


def list_documents(
    owner_id: str, limit: int = 100, next_token: str | None = None
) -> tuple[list[Document], str | None]:
    """List documents for owner. Returns (documents, next_token)."""
    return metadata_store.list_by_owner(owner_id, limit=limit, next_token=next_token)


def get_document(owner_id: str, filename: str) -> Document | None:
    """Get document by owner_id + filename."""
    return metadata_store.get_metadata(owner_id, filename)


def delete_document(owner_id: str, filename: str) -> bool:
    """
    Delete document: remove from S3, metadata, and S3 Vectors (when implemented).
    Returns True if document existed and was deleted, False if not found.
    """
    doc = metadata_store.get_metadata(owner_id, filename)
    if not doc:
        return False
    s3_storage.delete_document(owner_id, filename)
    vectors_storage.delete_vectors_by_document(owner_id, filename)
    metadata_store.delete_metadata(owner_id, filename)
    return True
