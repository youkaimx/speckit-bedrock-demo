"""S3 Vectors and Bedrock clients for embeddings and RAG. Placeholder until US2/US3."""

# T014: Configure S3 Vectors and Bedrock clients.
# Actual implementation in US2 (embedding_service, vectors storage) and US3 (retrieval, RAG).
# For US1 we only need document upload/list/delete; vector operations come in Phase 4/5.

import boto3

from src.api.config import get_settings
from src.observability.logging import get_logger


def get_vectors_client():
    """Placeholder: return client for S3 Vectors when implemented."""
    settings = get_settings()
    get_logger().debug(
        "S3 Vectors config (client not yet used)",
        s3_vectors_bucket_or_index=settings.s3_vectors_bucket_or_index,
        bedrock_model_id=settings.bedrock_model_id,
    )
    return None


def get_bedrock_client():
    """Placeholder: return Bedrock client when implemented."""
    settings = get_settings()
    get_logger().debug(
        "Bedrock client config",
        aws_region=settings.aws_region,
        bedrock_model_id=settings.bedrock_model_id,
        s3_vectors_bucket_or_index=settings.s3_vectors_bucket_or_index,
    )
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)
