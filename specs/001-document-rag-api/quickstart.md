# Quickstart: Document Upload and RAG Service

**Feature**: 001-document-rag-api  
**Date**: 2025-02-26

Minimal steps to run the API locally (or in a test environment) and exercise upload, list, RAG query, and delete. Assumes Python 3.12, AWS credentials (or LocalStack), and dependencies installed.

---

## Prerequisites

- Python 3.12
- AWS credentials (or LocalStack) with access to S3, S3 Vectors, and Bedrock (or mock)
- OAuth via **Amazon Cognito** (or test token for development). Per-user rate limits apply (429 when exceeded).

---

## 1. Clone and Branch

```bash
git clone <repo-url>
cd speckit-bedrock-demo
git checkout 001-document-rag-api
```

---

## 2. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

(Ensure `requirements.txt` includes FastAPI, uvicorn, boto3, structlog, opentelemetry-*, pypdf, markdown, httpx, pytest, pytest-asyncio.)

---

## 3. Configure Environment

Create `.env` (or set env vars):

```bash
# AWS
AWS_REGION=us-east-1
S3_BUCKET_DOCUMENTS=<your-bucket>
DYNAMODB_TABLE_METADATA=<your-document-metadata-table>
S3_VECTORS_BUCKET_OR_INDEX=<your-s3-vectors-bucket-or-index>   # S3 Vectors for embeddings
BEDROCK_MODEL_ID=<embedding-and-chat-model-ids>

# Auth (Cognito or test)
COGNITO_USER_POOL_ID=<pool-id>
COGNITO_CLIENT_ID=<client-id>
# or TEST_TOKEN=<jwt-for-dev>

# Optional: OTLP for observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

---

## 4. Run the API

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

API base URL: `http://localhost:8000`. OpenAPI docs: `http://localhost:8000/docs`.

---

## 5. Obtain a Token

- **Production**: Use Cognito (or your IdP) to obtain an access token.
- **Development**: Use a test token or Cognito test user; set `Authorization: Bearer <token>` on requests.

---

## 6. Upload a Document

**Upload and analyze** (immediate processing):

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/contract.pdf" \
  -F "mode=upload_and_analyze"
```

**Upload and queue** (pending for scheduled batch):

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/doc.md" \
  -F "mode=upload_and_queue"
```

Expect `201 Created` with `document_id` (filename), `format`, `processing_status`.

---

## 7. List Documents

```bash
curl -X GET http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN"
```

Expect `200 OK` with `documents` array (document_id = filename, format, status).

---

## 8. RAG Query

After at least one document is processed:

```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the termination clause?"}'
```

Expect `200 OK` with `answer` (and optionally `source_document_ids`). If no documents processed, expect a “no knowledge” style response.

---

## 9. Delete a Document

```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/<document_id>" \
  -H "Authorization: Bearer $TOKEN"
```

Expect `204 No Content`. Document and its embeddings are removed.

---

## 10. Run Tests

```bash
# Unit and contract tests
pytest tests/unit tests/contract -v

# Integration (requires AWS or LocalStack)
pytest tests/integration -v
```

---

## 11. Run Scheduled Batch (Upload and Queue)

If using a separate batch job (e.g. same app in “batch” mode or a scheduled task):

```bash
# Example: run batch processor once
python -m src.services.batch_process
```

Or trigger via ECS Scheduled Task / EventBridge at the configured interval.

---

## References

- **Spec**: [spec.md](./spec.md)
- **Plan**: [plan.md](./plan.md)
- **API contract**: [contracts/api-contract.md](./contracts/api-contract.md)
- **Data model**: [data-model.md](./data-model.md)
