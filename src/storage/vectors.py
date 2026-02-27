"""S3 Vectors and Bedrock clients for embeddings and RAG. Placeholder until US2/US3."""

# T014: Configure S3 Vectors and Bedrock clients.
# Actual implementation in US2 (embedding_service, vectors storage) and US3 (retrieval, RAG).
# For US1 we only need document upload/list/delete; vector operations come in Phase 4/5.

from src.api.config import get_settings


def get_vectors_client():
    """Placeholder: return client for S3 Vectors when implemented."""
    # S3 Vectors / Bedrock client setup in T014, T027, T032
    return None


def get_bedrock_client():
    """Placeholder: return Bedrock client when implemented."""
    settings = get_settings()
    import boto3

    return boto3.client("bedrock-runtime", region_name=settings.aws_region)
