# Tasks: Document Upload and RAG Service

**Input**: Design documents from `specs/001-document-rag-api/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Contract and integration test tasks are included in Polish phase; add earlier per story if TDD is desired.

**Organization**: Tasks are grouped by user story (US1 Upload, US2 Process, US3 RAG) to enable independent implementation and testing. Document identifier is **user-scoped filename** (one filename per user; re-upload with same filename replaces). Infrastructure via **Terraform** (AWS provider v6; terraform-aws-modules). **Per-user rate limits** (FR-013) and **429** in contract tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project** (per plan): `src/`, `tests/`, `terraform/` at repository root
- **Paths**: src/api/, src/services/, src/models/, src/storage/, src/observability/, terraform/

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per plan: src/api/, src/services/, src/models/, src/storage/, src/observability/, tests/contract/, tests/integration/, tests/unit/, terraform/
- [ ] T002 Initialize Python 3.12 project with FastAPI, uvicorn, boto3, pypdf, markdown, structlog, opentelemetry-api, opentelemetry-sdk, opentelemetry-exporter-otlp, httpx in requirements.txt (or pyproject.toml)
- [ ] T003 [P] Configure linting and formatting (e.g. ruff) in pyproject.toml or separate config

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure and Terraform that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Terraform (IR-001–IR-003: AWS provider v6, terraform-aws-modules)

- [ ] T004 [P] Add Terraform project with AWS provider v6 (hashicorp/aws >= 6.0) in terraform/main.tf, variables.tf, outputs.tf
- [ ] T005 [P] Add S3 bucket(s) for documents with encryption at rest (SSE-S3) using terraform-aws-modules in terraform/
- [ ] T006 [P] Add Cognito user pool and app client using terraform-aws-modules in terraform/
- [ ] T007 [P] Add ECS cluster, service, and task definition placeholders using terraform-aws-modules in terraform/
- [ ] T008 [P] Add DynamoDB table (or equivalent) for document metadata keyed by owner_id + filename per data-model.md in terraform/ (terraform-aws-modules if available)

### Application foundation

- [ ] T009 [P] Implement OAuth/Cognito authentication middleware (validate Bearer token, extract owner_id) in src/api/auth.py
- [ ] T010 [P] Setup FastAPI app and API routing structure (base path /api/v1) in src/api/main.py
- [ ] T011 Create Document domain model (filename, owner_id, format, size_bytes, uploaded_at, processing_status, processing_error, processed_at) in src/models/document.py — document identifier is filename per spec
- [ ] T012 Configure S3 client and document bucket access in src/storage/s3.py
- [ ] T013 Configure S3 Vectors and Bedrock clients for embeddings and RAG in src/storage/vectors.py and src/storage/bedrock.py (or under services)
- [ ] T014 [P] Configure structured logging (structlog, JSON, timestamp, level, message, request_id) in src/observability/logging.py
- [ ] T015 [P] Configure OpenTelemetry (metrics, traces, OTLP export) in src/observability/telemetry.py
- [ ] T016 Implement per-user rate limiter middleware (throttle by owner_id; return 429 when exceeded) per FR-013 in src/api/rate_limit.py
- [ ] T017 Setup environment configuration (e.g. pydantic-settings, .env) for AWS_REGION, S3_BUCKET_DOCUMENTS, S3_VECTORS_*, BEDROCK_*, COGNITO_*, OTEL_*, rate limit config per quickstart.md

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Upload Documents (Priority: P1) 🎯 MVP

**Goal**: Authenticated users can upload PDF/Markdown (upload and analyze or upload and queue), list their documents with status (document_id = filename), and delete a document by filename (and its embeddings).

**Independent Test**: Upload a PDF with upload_and_analyze and a file with upload_and_queue via API; list documents; delete one by filename; verify 401 without token; verify 429 when rate limit exceeded.

### Implementation for User Story 1

- [ ] T018 [P] [US1] Implement S3 document storage (upload object, get object, delete object; key by owner_id + filename) in src/storage/s3.py
- [ ] T019 [P] [US1] Implement document metadata store (create, list by owner_id, get by owner_id+filename, update status, delete) in src/storage/metadata.py
- [ ] T020 [US1] Implement upload service (validate 25 MB max, PDF/Markdown only, replace-on-same-filename) in src/services/upload_service.py
- [ ] T021 [US1] Implement POST /api/v1/documents (multipart file, mode=upload_and_analyze|upload_and_queue) and GET /api/v1/documents in src/api/routes/documents.py — response document_id is filename
- [ ] T022 [US1] Implement DELETE /api/v1/documents/{document_id} in src/api/routes/documents.py — document_id is filename (URL-encoded); remove from S3, metadata, and S3 Vectors per FR-007a
- [ ] T023 [US1] Add validation and error responses (400 format/size, 401, 403, 404, 429) per contracts/api-contract.md in src/api/routes/documents.py

**Checkpoint**: User Story 1 complete - upload, list, delete by filename work; processing triggered for upload_and_analyze (see US2)

---

## Phase 4: User Story 2 - Process Documents and Build Searchable Knowledge (Priority: P2)

**Goal**: Documents are analyzed via Bedrock to produce embeddings stored in S3 Vectors; processing runs immediately after upload_and_analyze or via **daily (or configurable)** scheduled batch for upload_and_queue; successful docs scheduled for deletion from S3.

**Independent Test**: Upload with upload_and_analyze and verify processing runs; upload with upload_and_queue and run batch once; verify embeddings in S3 Vectors and document status updated.

### Implementation for User Story 2

- [ ] T024 [P] [US2] Implement text extraction (PDF via pypdf, Markdown) in src/services/extract_service.py
- [ ] T025 [P] [US2] Implement Bedrock embedding invocation in src/services/embedding_service.py
- [ ] T026 [US2] Implement S3 Vectors storage (store vectors with document_filename, owner_id metadata; delete vectors by owner_id + filename) in src/storage/vectors.py
- [ ] T027 [US2] Implement processing pipeline (extract → embed → store in S3 Vectors → update document status → schedule S3 object for deletion) in src/services/process_service.py
- [ ] T028 [US2] Trigger processing asynchronously on upload_and_analyze from upload service in src/services/upload_service.py
- [ ] T029 [US2] Implement scheduled batch job for pending documents (upload_and_queue) in src/services/batch_process.py — schedule **daily** (or configurable) via ECS Scheduled Task or EventBridge
- [ ] T030 [US2] Add processing failure handling (set status failed, processing_error; no partial embeddings; do not schedule S3 delete) in src/services/process_service.py

**Checkpoint**: User Story 2 complete - immediate and batch processing work; embeddings in S3 Vectors

---

## Phase 5: User Story 3 - Ask Questions via RAG (Priority: P3)

**Goal**: Authenticated users can submit a question and receive an answer grounded in their processed documents (retrieve from S3 Vectors, then Bedrock). source_document_ids in response are filenames.

**Independent Test**: After at least one document is processed, POST /rag/query with a question; receive grounded answer. With no documents processed, receive clear "no knowledge" message.

### Implementation for User Story 3

- [ ] T031 [US3] Implement retrieval from S3 Vectors (query by embedding, filter by owner_id) in src/services/retrieval_service.py
- [ ] T032 [US3] Implement RAG service (retrieve chunks → build context → Bedrock InvokeModel for answer) in src/services/rag_service.py
- [ ] T033 [US3] Implement POST /api/v1/rag/query (accept question, return answer and optional source_document_ids as filenames) in src/api/routes/rag.py
- [ ] T034 [US3] Handle empty vector store and no relevant chunks (return clear "no knowledge" message, do not fabricate) in src/services/rag_service.py

**Checkpoint**: All user stories complete - upload, process, RAG query, delete by filename

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Containerization, CI, tests, and quickstart validation

- [ ] T035 [P] Add Dockerfile for containerized run (Python 3.12, FastAPI app)
- [ ] T036 [P] Add GitHub Actions workflow for CI (install deps, lint, test, build image) in .github/workflows/ci.yml
- [ ] T037 Run quickstart.md validation and fix steps if needed
- [ ] T038 [P] Add contract tests for POST/GET/DELETE /documents and POST /rag/query per contracts/api-contract.md in tests/contract/ — include 429 for per-user rate limit
- [ ] T039 [P] Add integration tests for upload, process, RAG, delete flows in tests/integration/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3–5)**: All depend on Foundational
  - US1 (Phase 3) can be done first; US2 depends on US1 for upload API and trigger; US3 depends on US2 for embeddings
- **Polish (Phase 6)**: Depends on completion of desired user stories

### User Story Dependencies

- **US1 (P1)**: After Foundational only - upload, list, delete by filename
- **US2 (P2)**: After Foundational; uses US1 upload flow and metadata - process, batch (daily/configurable), S3 Vectors
- **US3 (P3)**: After US2 (needs embeddings in S3 Vectors) - RAG query

### Within Each User Story

- Storage/model tasks before services; services before routes
- T018–T019 can run in parallel; T024–T025 can run in parallel

### Parallel Opportunities

- Phase 1: T003 [P]
- Phase 2: T004–T008 [P] (Terraform); T009, T010, T012, T014, T015 [P] (app foundation)
- Phase 3: T018, T019 [P]; Phase 4: T024, T025 [P]
- Phase 6: T035, T036, T038, T039 [P]

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup  
2. Complete Phase 2: Foundational (Terraform + app foundation + rate limiter)  
3. Complete Phase 3: User Story 1 (upload, list, delete by filename)  
4. **STOP and VALIDATE**: Test upload/list/delete via API; verify 429 when rate limit exceeded  
5. Deploy/demo if ready  

### Incremental Delivery

1. Setup + Foundational → foundation ready  
2. US1 → upload, list, delete by filename (MVP)  
3. US2 → processing (immediate + daily batch), S3 Vectors  
4. US3 → RAG query  
5. Polish → Docker, CI, contract tests (incl. 429), integration tests  

### Parallel Team Strategy

- After Foundational: one developer on US1, another can start US2 (extract/embedding services); US3 after US2.

---

## Notes

- [P] = parallelizable (different files, no dependency on same-phase incomplete tasks)
- [USn] = maps to user story for traceability
- Document identifier = **filename** (user-scoped); replace-on-same-filename and 25 MB validation in US1 (T020, T023)
- Terraform: AWS provider v6; use terraform-aws-modules (Anton Babenko) per IR-003
- Per-user rate limits (FR-013) and 429 in contract tests (T038)
