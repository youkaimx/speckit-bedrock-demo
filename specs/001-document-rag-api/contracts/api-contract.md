# API Contract: Document Upload and RAG Service

**Feature**: 001-document-rag-api  
**Date**: 2025-02-26

REST API surface for upload (with modes), list, delete, and RAG query. All endpoints require OAuth (Bearer token) via **Amazon Cognito**. **Document identifier** is the user-scoped **filename** (one filename per user; re-upload with same filename replaces). Base path: `/api/v1` (or as configured). **Per-user rate limits** apply; excess requests return `429 Too Many Requests`.

---

## Authentication

- **Scheme**: OAuth 2.0 Bearer token (e.g. Cognito JWT).
- **Header**: `Authorization: Bearer <access_token>`
- **Behavior**: All endpoints below MUST return `401 Unauthorized` if the token is missing or invalid. Responses MUST be scoped to the authenticated user (`owner_id` from token).

---

## 1. Upload Document

**POST** `/documents`

**Purpose**: Upload a PDF or Markdown file. Two modes: **upload and analyze** (store + trigger immediate processing) or **upload and queue** (store only; process in scheduled batch).

**Request**:
- **Content-Type**: `multipart/form-data`
- **Body**:
  - `file` (required): PDF or Markdown file. Max size 25 MB.
  - `mode` (required): `upload_and_analyze` \| `upload_and_queue`
  - `name` (optional): Filename override; if omitted, use filename from `file`. This is the **document identifier** (user-scoped); same name under same user → replace existing document.

**Success**: `201 Created`
- **Body**: `{ "document_id": "<filename>", "format": "pdf"|"markdown", "size_bytes": <n>, "uploaded_at": "<ISO8601>", "processing_status": "pending"|"processing" }` — `document_id` is the user-scoped filename (e.g. `contract.pdf`).
- For `upload_and_analyze`, `processing_status` may be `processing` immediately.

**Errors**:
- `400 Bad Request`: Invalid format (not PDF/Markdown), missing `file` or `mode`, or file &gt; 25 MB. Body: `{ "error": "<message>" }`
- `401 Unauthorized`: Missing or invalid token.
- `429 Too Many Requests`: Per-user rate limit exceeded (FR-013).

**Replace behavior**: If a document with the same filename (and same owner) already exists, the server MUST replace it (overwrite), re-process, and refresh embeddings; response is same shape with `document_id` equal to that filename.

---

## 2. List Documents

**GET** `/documents`

**Purpose**: Return the authenticated user’s documents with identifiers and metadata (name, type, upload time, processing status).

**Request**: No body. Optional query: `limit`, `next_token` (or equivalent) for pagination.

**Success**: `200 OK`
- **Body**: `{ "documents": [ { "document_id": "<filename>", "format": "pdf"|"markdown", "size_bytes": <n>, "uploaded_at": "<ISO8601>", "processing_status": "pending"|"processing"|"processed"|"failed", "processing_error": "<optional>" } ], "next_token": "<optional>" }` — `document_id` is the user-scoped filename.

**Errors**:
- `401 Unauthorized`: Missing or invalid token.
- `429 Too Many Requests`: Per-user rate limit exceeded.

---

## 3. Delete Document

**DELETE** `/documents/{document_id}`

**Purpose**: Explicitly delete a document and its embeddings. Document and its vectors MUST be removed so it no longer contributes to RAG (FR-007a). `document_id` is the user-scoped **filename** (URL-encoded if needed).

**Request**: Path parameter `document_id` (filename; owner is implied by token).

**Success**: `204 No Content` (no body).

**Errors**:
- `401 Unauthorized`: Missing or invalid token.
- `403 Forbidden`: Document exists but belongs to another user (or equivalent).
- `404 Not Found`: No document with that filename for this user.
- `429 Too Many Requests`: Per-user rate limit exceeded.

---

## 4. RAG Query

**POST** `/rag/query`

**Purpose**: Submit a natural-language question; return an answer grounded in the user’s processed documents (retrieval from vector store + foundation model).

**Request**:
- **Content-Type**: `application/json`
- **Body**: `{ "question": "<natural-language question>" }`

**Success**: `200 OK`
- **Body**: `{ "answer": "<grounded answer>", "source_document_ids": ["<filename1>", ...] }` (or equivalent; `source_document_ids` optional; values are filenames)
- If no relevant content: `{ "answer": "<no relevant content message>", "source_document_ids": [] }` (or equivalent; MUST NOT fabricate answer).

**Errors**:
- `400 Bad Request`: Missing `question` or invalid body.
- `401 Unauthorized`: Missing or invalid token.
- `429 Too Many Requests`: Per-user rate limit exceeded.
- `503 Service Unavailable` or `200` with “no knowledge” message when vector store is empty or no documents processed (per spec: return clear message, do not fabricate).

---

## Common Conventions

- **Request ID**: Clients may send `X-Request-ID`; server SHOULD include it in structured logs and optionally in response headers for correlation.
- **Structured errors**: Error bodies SHOULD be JSON when possible, e.g. `{ "error": "<code or message>" }`.
- **Idempotency**: Upload replace-on-same-name is defined; delete is idempotent (204 even if already deleted, or 404).

---

## Contract Tests

Contract tests MUST verify:
- Upload (both modes) returns 201 and expected shape; reject &gt;25 MB and non-PDF/Markdown. `document_id` in response is the filename.
- List returns 200 and only the authenticated user’s documents (document_id = filename).
- Delete returns 204 for own document (by filename); 404 for unknown filename; 403 for other user’s document (if applicable).
- RAG query returns 200 with `answer`; unauthenticated request returns 401.
- Per-user rate limit: requests exceeding limit return 429.
