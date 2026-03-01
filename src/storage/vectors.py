"""S3 Vectors and Bedrock clients; store/delete vectors by owner_id and document filename."""

import boto3

from src.api.config import get_settings
from src.observability.logging import get_logger


# Vector key format for delete-by-document: owner_id/filename/chunk_index
def _vector_key(owner_id: str, document_filename: str, chunk_index: int) -> str:
    return f"{owner_id}/{document_filename}/{chunk_index}"


def get_vectors_client():
    """Return S3 Vectors client for put_vectors, delete_vectors, list_vectors, query_vectors."""
    settings = get_settings()
    kwargs = {"region_name": settings.aws_region}
    endpoint = (settings.aws_endpoint_url or "").strip()
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    get_logger().debug(
        "S3 Vectors client config",
        aws_region=settings.aws_region,
        s3_vectors_bucket=settings.s3_vectors_bucket_or_index,
        s3_vectors_index=settings.s3_vectors_index,
    )
    return boto3.client("s3vectors", **kwargs)


def get_bedrock_client():
    """Return Bedrock runtime client for InvokeModel (embeddings and RAG)."""
    settings = get_settings()
    get_logger().debug(
        "Bedrock client config",
        aws_region=settings.aws_region,
        bedrock_model_id=settings.bedrock_model_id,
        s3_vectors_bucket_or_index=settings.s3_vectors_bucket_or_index,
    )
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)


def store_vectors(
    owner_id: str,
    document_filename: str,
    vectors: list[tuple[list[float], str]],
) -> None:
    """
    Store vectors in S3 Vectors index. Each item is (embedding, text).
    Key format: owner_id/document_filename/chunk_index. Metadata: owner_id, document_filename, text.
    """
    settings = get_settings()
    bucket = settings.s3_vectors_bucket_or_index
    index = settings.s3_vectors_index
    if not bucket or not index:
        raise ValueError("S3_VECTORS_BUCKET_OR_INDEX and index must be set to store vectors")
    client = get_vectors_client()
    payload = []
    for i, (embedding, text) in enumerate(vectors):
        key = _vector_key(owner_id, document_filename, i)
        # S3 Vectors requires float32
        float32_list = [float(x) for x in embedding]
        payload.append(
            {
                "key": key,
                "data": {"float32": float32_list},
                "metadata": {
                    "owner_id": owner_id,
                    "document_filename": document_filename,
                    "text": text[: 64 * 1024],  # metadata size limit; truncate if needed
                },
            }
        )
    if not payload:
        return
    client.put_vectors(
        vectorBucketName=bucket,
        indexName=index,
        vectors=payload,
    )


def query_vectors(
    owner_id: str,
    query_vector: list[float],
    top_k: int = 10,
) -> list[tuple[str, str]]:
    """
    Query S3 Vectors for nearest neighbors to query_vector, filtered by owner_id.
    Returns list of (text, document_filename) from metadata. Empty if bucket/index not set.
    """
    settings = get_settings()
    bucket = settings.s3_vectors_bucket_or_index
    index = settings.s3_vectors_index
    if not bucket or not index:
        return []
    client = get_vectors_client()
    float32_list = [float(x) for x in query_vector]
    try:
        resp = client.query_vectors(
            vectorBucketName=bucket,
            indexName=index,
            topK=top_k,
            queryVector={"float32": float32_list},
            filter={"owner_id": {"$eq": owner_id}},
            returnMetadata=True,
            returnDistance=True,
        )
    except Exception:
        return []
    out = []
    for v in resp.get("vectors", []):
        meta = v.get("metadata") or {}
        text = meta.get("text") or ""
        doc_fn = meta.get("document_filename") or ""
        if text or doc_fn:
            out.append((text, doc_fn))
    return out


def delete_vectors_by_document(owner_id: str, document_filename: str) -> None:
    """
    Delete all vectors for a document (owner_id + filename). Lists vectors by key prefix and deletes.
    """
    settings = get_settings()
    bucket = settings.s3_vectors_bucket_or_index
    index = settings.s3_vectors_index
    if not bucket or not index:
        return
    prefix = f"{owner_id}/{document_filename}/"
    client = get_vectors_client()
    keys_to_delete = []
    next_token = None
    while True:
        kwargs = {
            "vectorBucketName": bucket,
            "indexName": index,
            "maxResults": 500,
            "returnData": False,
            "returnMetadata": False,
        }
        if next_token:
            kwargs["nextToken"] = next_token
        resp = client.list_vectors(**kwargs)
        for v in resp.get("vectors", []):
            k = v.get("key", "")
            if k.startswith(prefix):
                keys_to_delete.append(k)
        next_token = resp.get("nextToken")
        if not next_token:
            break
    if not keys_to_delete:
        return
    client.delete_vectors(
        vectorBucketName=bucket,
        indexName=index,
        keys=keys_to_delete,
    )
