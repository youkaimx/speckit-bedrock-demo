"""Environment configuration (pydantic-settings).

Values are read from (lowest to highest precedence):
  1. Defaults on each field (e.g. default="INFO")
  2. The .env file (if present; path from env_file)
  3. The process environment (os.environ)

So environment variables override .env, and .env overrides defaults. If .env
is missing, only env vars and defaults are used.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AWS (for LocalStack set AWS_ENDPOINT_URL=http://localhost:4566; restart app after changing .env)
    aws_region: str = "us-east-1"
    aws_endpoint_url: str | None = Field(default=None, validation_alias="AWS_ENDPOINT_URL")
    s3_bucket_documents: str = Field(default="", validation_alias="S3_BUCKET_DOCUMENTS")
    dynamodb_table_metadata: str = Field(default="", validation_alias="DYNAMODB_TABLE_METADATA")
    s3_vectors_bucket_or_index: str | None = None
    s3_vectors_index: str = Field(default="default", validation_alias="S3_VECTORS_INDEX")
    bedrock_model_id: str | None = None
    bedrock_rag_model_id: str | None = Field(default=None, validation_alias="BEDROCK_RAG_MODEL_ID")

    # Cognito
    cognito_user_pool_id: str | None = None
    cognito_client_id: str | None = None

    # OTLP / observability
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "document-rag-api"

    # Logging (plan Logging: config file / .env; CLI overrides when using run entrypoint)
    log_level: str = Field(default="DEBUG", validation_alias="LOG_LEVEL")

    # Rate limit (per-user requests per window)
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
