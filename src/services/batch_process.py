"""Scheduled batch job for pending documents (upload_and_queue). Invoke daily via ECS Scheduled Task or EventBridge."""

from src.models.document import ProcessingStatus
from src.observability.logging import configure_logging
from src.services import process_service
from src.storage import metadata as metadata_store


def run_pending_batch(limit: int = 500) -> int:
    """
    Process all documents with status pending (upload_and_queue). Returns count processed.
    Schedule this daily (or configurable) via ECS Scheduled Task or EventBridge.
    """
    processed = 0
    next_token = None
    while True:
        docs, next_token = metadata_store.list_by_status(
            ProcessingStatus.PENDING, limit=limit, next_token=next_token
        )
        for doc in docs:
            process_service.process_document(doc.owner_id, doc.filename)
            processed += 1
        if not next_token:
            break
    return processed


if __name__ == "__main__":
    configure_logging()
    run_pending_batch()
