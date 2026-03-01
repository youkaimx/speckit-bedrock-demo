"""Document metadata store (DynamoDB): create, list by owner_id, get, update status, delete."""

import contextlib
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from src.api.config import get_settings
from src.models.document import Document, DocumentFormat, ProcessingStatus
from src.observability.logging import get_logger


def _get_table():
    """DynamoDB table: single place where the DynamoDB client/resource is created.
    Uses get_settings(); for LocalStack set AWS_ENDPOINT_URL=http://localhost:4566
    and DYNAMODB_TABLE_METADATA=<table-name> in .env, then restart the app."""
    settings = get_settings()
    kwargs = {"region_name": settings.aws_region}
    endpoint = (settings.aws_endpoint_url or "").strip()
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    get_logger().debug(
        "DynamoDB client config",
        aws_region=settings.aws_region,
        aws_endpoint_url=settings.aws_endpoint_url or None,
        dynamodb_table_metadata=settings.dynamodb_table_metadata,
    )
    dynamodb = boto3.resource("dynamodb", **kwargs)
    return dynamodb.Table(settings.dynamodb_table_metadata)


def _doc_to_item(doc: Document) -> dict:
    item = {
        "owner_id": doc.owner_id,
        "filename": doc.filename,
        "format": doc.format.value if hasattr(doc.format, "value") else doc.format,
        "size_bytes": doc.size_bytes,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "processing_status": doc.processing_status.value
        if hasattr(doc.processing_status, "value")
        else doc.processing_status,
    }
    if doc.processing_error is not None:
        item["processing_error"] = doc.processing_error
    if doc.processed_at is not None:
        item["processed_at"] = doc.processed_at.isoformat()
    return item


def _parse_dt(s: str) -> datetime:
    s = s.replace("Z", "+00:00")
    if s.endswith("+00:00") or "-" in s[-6:]:
        return datetime.fromisoformat(s)
    return datetime.fromisoformat(s)


def _item_to_doc(item: dict) -> Document:
    return Document(
        owner_id=item["owner_id"],
        filename=item["filename"],
        format=DocumentFormat(item["format"]),
        size_bytes=int(item["size_bytes"]),
        uploaded_at=_parse_dt(item["uploaded_at"]),
        processing_status=ProcessingStatus(item["processing_status"]),
        processing_error=item.get("processing_error"),
        processed_at=_parse_dt(item["processed_at"]) if item.get("processed_at") else None,
    )


def create_metadata(doc: Document) -> None:
    """Create document metadata record (replace if same owner_id+filename)."""
    table = _get_table()
    table.put_item(Item=_doc_to_item(doc))


def list_by_owner(
    owner_id: str,
    limit: int = 100,
    next_token: str | None = None,
) -> tuple[list[Document], str | None]:
    """List documents by owner_id. Returns (documents, next_token)."""
    table = _get_table()
    params = {
        "KeyConditionExpression": "owner_id = :oid",
        "ExpressionAttributeValues": {":oid": owner_id},
        "Limit": limit,
    }
    if next_token:
        params["ExclusiveStartKey"] = {"owner_id": owner_id, "filename": next_token}
    resp = table.query(**params)
    items = resp.get("Items", [])
    docs = [_item_to_doc(i) for i in items]
    last_key = resp.get("LastEvaluatedKey")
    next_tok = last_key.get("filename") if last_key else None
    return docs, next_tok


def list_by_status(
    status: ProcessingStatus,
    limit: int = 100,
    next_token: dict | None = None,
) -> tuple[list[Document], dict | None]:
    """List documents by processing_status (scan with filter). For batch job. Returns (documents, next_token)."""
    table = _get_table()
    params = {
        "FilterExpression": "processing_status = :s",
        "ExpressionAttributeValues": {":s": status.value if hasattr(status, "value") else status},
        "Limit": limit,
    }
    if next_token:
        params["ExclusiveStartKey"] = next_token
    resp = table.scan(**params)
    items = resp.get("Items", [])
    docs = [_item_to_doc(i) for i in items]
    last_key = resp.get("LastEvaluatedKey")
    return docs, last_key


def get_metadata(owner_id: str, filename: str) -> Document | None:
    """Get document by owner_id + filename."""
    table = _get_table()
    try:
        resp = table.get_item(Key={"owner_id": owner_id, "filename": filename})
        item = resp.get("Item")
        if not item:
            return None
        return _item_to_doc(item)
    except ClientError:
        return None


def update_status(
    owner_id: str,
    filename: str,
    status: ProcessingStatus,
    processing_error: str | None = None,
    processed_at: datetime | None = None,
    clear_processing_error: bool = False,
) -> None:
    """Update processing status (and optional processing_error, processed_at).
    Set clear_processing_error=True to REMOVE processing_error (e.g. when starting or on success)."""
    table = _get_table()
    expr = "SET processing_status = :s"
    values = {":s": status.value if hasattr(status, "value") else status}
    if processing_error is not None:
        expr += ", processing_error = :e"
        values[":e"] = processing_error
    if processed_at is not None:
        expr += ", processed_at = :p"
        values[":p"] = processed_at.isoformat()
    if clear_processing_error:
        expr += " REMOVE processing_error"
    table.update_item(
        Key={"owner_id": owner_id, "filename": filename},
        UpdateExpression=expr,
        ExpressionAttributeValues=values,
    )


def delete_metadata(owner_id: str, filename: str) -> None:
    """Delete metadata record (idempotent)."""
    table = _get_table()
    with contextlib.suppress(ClientError):
        table.delete_item(Key={"owner_id": owner_id, "filename": filename})
