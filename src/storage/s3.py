"""S3 client and document bucket access. Key by owner_id + filename."""

import contextlib
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from src.api.config import get_settings


def get_s3_client():
    settings = get_settings()
    kwargs = {"region_name": settings.aws_region}
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return boto3.client("s3", **kwargs)


def document_key(owner_id: str, filename: str) -> str:
    """S3 object key for a document: owner_id/filename."""
    return f"{owner_id}/{filename}"


def upload_document(
    owner_id: str,
    filename: str,
    body: BinaryIO,
    content_type: str,
) -> None:
    """Upload object to S3; key = owner_id/filename."""
    client = get_s3_client()
    bucket = get_settings().s3_bucket_documents
    key = document_key(owner_id, filename)
    client.upload_fileobj(
        body,
        bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )


def get_document(owner_id: str, filename: str) -> bytes | None:
    """Get object bytes; return None if not found."""
    client = get_s3_client()
    bucket = get_settings().s3_bucket_documents
    key = document_key(owner_id, filename)
    try:
        resp = client.get_object(Bucket=bucket, Key=key)
        return resp["Body"].read()
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise


def delete_document(owner_id: str, filename: str) -> None:
    """Delete object from S3 (idempotent; no error if key missing)."""
    client = get_s3_client()
    bucket = get_settings().s3_bucket_documents
    key = document_key(owner_id, filename)
    with contextlib.suppress(ClientError):
        client.delete_object(Bucket=bucket, Key=key)
