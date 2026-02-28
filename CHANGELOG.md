# Changelog

All notable changes to the Document Upload and RAG Service are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **Constitution (v1.2.0)**: Principle VII. Documentation — document every class, function, and resource; project must describe what it does and how to run it.
- **Plan – Logging**: Structured logging with configurable verbosity via command line (`--log-level`) and configuration file (e.g. `LOG_LEVEL` in `.env`). Command line overrides config when both are set.
- **Plan – Cloud infrastructure phasing**: Infrastructure split into at least two steps; Step 1 = minimum for initial testing (S3 bucket + DynamoDB table only).
- **Config**: `LOG_LEVEL` setting (env `LOG_LEVEL`); docstring describing precedence (defaults &lt; .env &lt; process environment). Validation aliases for `AWS_ENDPOINT_URL`, `S3_BUCKET_DOCUMENTS`, `DYNAMODB_TABLE_METADATA`.
- **Run entrypoint** (`python -m src.api.run`): Optional `--log-level`, `--host`, `--port`, `--reload`. Sets `LOG_LEVEL` in environment before starting uvicorn so CLI overrides `.env`.
- **Observability**: `configure_logging(level=...)` in `src/observability/logging.py` uses config when `level` not passed; level configurable via config or CLI.
- **DEBUG logging**: When `LOG_LEVEL=DEBUG`, log settings used when opening AWS clients: DynamoDB (region, endpoint, table), S3 (region, endpoint, bucket), Bedrock/Vectors (region, model, vectors bucket), Auth/Cognito (pool id, client id).
- **Documents API**: 503 Service Unavailable with error details when S3/DynamoDB raise `ClientError` (e.g. bucket or table missing with LocalStack).
- **Docs**: LOCAL_TESTING — Terraform Step 1 note, LOG_LEVEL and run entrypoint, 503 troubleshooting, DynamoDB location; quickstart — LOG_LEVEL in env, Option B run entrypoint with `--log-level`.

### Changed

- **Terraform**: Step 1 only — S3 bucket (documents) and DynamoDB table (metadata) retained; Cognito, ECS, S3 Vectors, and related outputs/variables removed for later implementation.
- **Storage**: S3 and DynamoDB client creation use stripped `aws_endpoint_url` for consistency; DEBUG logs added at client creation.
- **Env template**: `.env.example` replaced by `env.example` with LocalStack-oriented defaults (e.g. `AWS_ENDPOINT_URL`, bucket/table names) and optional `LOG_LEVEL=DEBUG`.

### Fixed

- Smoke test (Option 3): Documented response is 503 (not 500) when storage is not configured.

---

## [0.1.0] – baseline

- Document Upload and RAG API (FastAPI): upload, list, delete documents by filename; auth via Bearer (dev token or JWT); per-user rate limits; structured logging (structlog); OpenTelemetry placeholders.
- Terraform: AWS provider v6; S3 bucket (SSE-S3); DynamoDB table (owner_id + filename); Terraform Cloud backend.
- Local testing: Real AWS (Terraform + .env), LocalStack (S3 + DynamoDB), smoke test without storage.
