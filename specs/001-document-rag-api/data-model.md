# Data Model: Document Upload and RAG Service

**Feature**: 001-document-rag-api  
**Date**: 2025-02-26

Domain entities, storage mapping, and lifecycle. Aligns with [spec.md](./spec.md) Key Entities and FRs.

---

## 1. Document

**Definition**: A user-provided file (PDF or Markdown) stored in object storage; represents one upload and its processing lifecycle. **Document identity is the user-scoped filename** (one filename per user; re-upload with same filename replaces) per spec.

| Attribute | Type | Description |
|-----------|------|-------------|
| **filename** | string | User-scoped document identifier (e.g. `contract.pdf`). One per user; same filename → replace. Used in API and S3/vector keys. |
| **owner_id** | string | OAuth subject / user identifier; all access scoped by this. |
| **format** | enum | `pdf` \| `markdown` |
| **size_bytes** | integer | File size; MUST NOT exceed 25 MB (26,214,400 bytes). |
| **uploaded_at** | datetime (ISO 8601) | When the document was uploaded. |
| **processing_status** | enum | `pending` \| `processing` \| `processed` \| `failed` |
| **processing_error** | string (optional) | Present when status is `failed`; reason for failure. |
| **processed_at** | datetime (optional) | When embedding completed (status `processed`). |

**Storage**:  
- **Raw file**: S3 object at a key derived from `owner_id` and `filename`. Deleted (or lifecycle) after embeddings created (FR-005).  
- **Metadata**: DynamoDB item keyed by `owner_id` + `filename` (or equivalent table), or derived from S3 list + object metadata.  

**Lifecycle**:
- **Create**: On upload (upload and analyze, or upload and queue). Status `pending` or immediately `processing` for “upload and analyze”.
- **Update**: Status transitions: `pending` → `processing` → `processed` or `failed`. Replace: re-upload with same owner_id + filename overwrites and re-processes (FR-001).
- **Delete**: Explicit delete removes S3 object (if present) and all embeddings for this document (owner_id + filename) (FR-007a).

**Uniqueness**: Per owner, filename is unique. Composite key (owner_id, filename). Replace-on-same-name: same owner_id + same filename → replace existing document.

---

## 2. Embedding

**Definition**: Vector representation of document content produced by the foundation model; stored in the vector store and used for RAG retrieval.

| Attribute | Type | Description |
|-----------|------|-------------|
| **document_filename** | string | Links to Document.filename (user-scoped); used to delete all vectors for a document on delete. |
| **owner_id** | string | Same as Document.owner_id; used for RAG scoping (retrieve only this owner’s vectors). |
| **chunk_index** | integer (optional) | If document is chunked, index of chunk. |
| **vector** | float[] | Embedding vector (dimension from model, e.g. 1024). |
| **text** | string (optional) | Source text for this chunk; stored for retrieval and context in RAG. |

**Storage**: Amazon S3 Vectors. Each vector record includes `document_filename` (or document key) and `owner_id` in metadata for filtering and delete-by-document. S3 Vectors provides native vector storage and query in S3 (Bedrock integration; cost-optimized; sub-second query).

**Lifecycle**:
- **Create**: When processing runs (immediate after “upload and analyze”, or in scheduled batch for “upload and queue”). One or more vectors per document (chunked).
- **Delete**: When user deletes document, all vectors with that document (owner_id + filename) MUST be removed (FR-007a).
- **Retention**: Indefinite until user deletes document or account (FR-005).

---

## 3. RAG Query (Logical)

**Definition**: A user question plus retrieved context and the foundation model’s answer; not necessarily persisted.

| Attribute | Type | Description |
|-----------|------|-------------|
| **question** | string | User’s natural-language question. |
| **answer** | string | Foundation model response grounded in retrieved chunks. |
| **source_document_filenames** | string[] (optional) | Document filenames that contributed chunks to the answer (for attribution). |

**Storage**: No mandatory persistence; can be logged or stored for audit if required later. API returns `answer` (and optionally document filenames used).

---

## 4. Processing Queue (Upload and Queue)

**Definition**: Documents with status `pending` that were uploaded with “upload and queue”; processed by the scheduled batch.

**Representation**: No separate table required; “queue” is the set of Document records with `processing_status = pending` and upload mode “queue”. Batch job queries these and processes them, then sets status to `processing` → `processed` or `failed`.

---

## 5. Identity and Scoping

- **owner_id**: From OAuth token (e.g. Cognito `sub`). Every S3 key, DynamoDB key, and vector metadata MUST include owner_id so that list/delete/RAG are strictly per-user (FR-007).
- **document identifier**: User-scoped **filename** (one per user). Same owner + same filename → replace. Used in API, S3 key, DynamoDB, and vector metadata. No separate UUID; filename is the id.

---

## 6. Validation Rules (from Spec)

- **Max size**: 25 MB per document (FR-001). Reject at upload if exceeded.
- **Format**: PDF or Markdown only; reject others at upload (FR-001).
- **Replace**: Same owner + same filename on upload → replace existing document and re-process (FR-001, Clarifications).
