"""Environment configuration (pydantic-settings)."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AWS (set AWS_ENDPOINT_URL for LocalStack, e.g. http://localhost:4566)
    aws_region: str = "us-east-1"
    aws_endpoint_url: Optional[str] = None
    s3_bucket_documents: str = ""
    dynamodb_table_metadata: str = ""
    s3_vectors_bucket_or_index: Optional[str] = None
    bedrock_model_id: Optional[str] = None

    # Cognito
    cognito_user_pool_id: Optional[str] = None
    cognito_client_id: Optional[str] = None

    # OTLP / observability
    otel_exporter_otlp_endpoint: Optional[str] = None
    otel_service_name: str = "document-rag-api"

    # Rate limit (per-user requests per window)
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
