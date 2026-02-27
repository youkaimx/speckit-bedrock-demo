# Feature Specification: Document Upload and RAG Service

**Feature Branch**: `001-document-rag-api`
**Created**: 2025-02-26
**Status**: Draft
**Input**: User description: document upload (PDF/Markdown) stored in object storage; analysis by foundation model via endpoint; embeddings stored in vector store; RAG queries answered by foundation model; documents scheduled for deletion after embeddings created; containerized service; API with OAuth; AWS services; Python; CI with GitHub Actions.

## Clarifications

### Session 2025-02-26

- Q: When a user uploads a file with the same name (or same content) as an existing document, what should the system do? → A: Replace (overwrite existing document; same identifier; re-process and refresh embeddings).
- Q: When should the system run analysis and create embeddings for an uploaded document? → A: Two modes — (1) Upload and analyze: process immediately after upload; (2) Upload and queue: store only, process via scheduled batch.
- Q: What is the maximum allowed size for a single uploaded document (PDF or Markdown)? → A: 25 MB per document (primary use case: legal documents; very large bundles should be split before upload).
- Q: How long should the system retain embeddings (and the ability to answer RAG questions from them)? → A: Indefinite until user deletes (embedding retained until the user explicitly deletes the document or account; no automatic expiry).
- Q: Must the system support an explicit "delete document" (and its embeddings) action so the user can remove a document and stop RAG from using it? → A: Yes; system MUST support explicit delete (document and its embeddings); user can remove a document and its RAG contribution.
- Q: Which vector store should the system use for storing and querying embeddings (and thus for RAG retrieval)? → A: Amazon S3 Vectors (native vector storage and query in S3; Bedrock integration; cost-optimized).
- Q: How should project infrastructure be defined and provisioned? → A: All infrastructure MUST be generated via Terraform using the AWS provider v6. Where Terraform modules are used, use those from terraform-aws-modules authored by Anton Babenko.
- Q: Is the document identifier user-provided or system-generated? → A: Filename as identifier — document identity is the user-scoped filename; one filename per user; re-upload with same filename replaces.
- Q: How often does the scheduled batch run for "upload and queue" documents? → A: Daily (or configurable); batch runs once per day or as configured; longest wait for queued processing.
- Q: Which OAuth/identity provider should the API use? → A: Amazon Cognito (managed user pools and/or OIDC; all auth on AWS).
- Q: Should the API enforce rate limiting or throttling? → A: Per-user rate limits; throttle by authenticated user (e.g. requests per minute per user).
- Q: What encryption is required for API and stored data? → A: TLS in transit for all API and service traffic; encryption at rest using AWS defaults (e.g. SSE-S3 for S3 and equivalent for other storage).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload Documents (Priority: P1)

An authenticated user uploads one or more documents (PDF or Markdown) using one of two modes: **Upload and analyze** (store and trigger immediate processing) or **Upload and queue** (store only; processing runs later via scheduled batch). The system accepts the files, validates format and size, and stores them in durable object storage. The user receives confirmation and can see the list of uploaded documents they own, including processing status (e.g. pending, processing, processed).

**Why this priority**: Upload is the entry point; without it, no documents exist to analyze or query.

**Independent Test**: User uploads a PDF via “upload and analyze” and a Markdown file via “upload and queue” via the API; verifies both are stored and listed with correct status; can be tested without RAG.

**Acceptance Scenarios**:

1. **Given** the user is authenticated, **When** they upload a valid PDF or Markdown file with “upload and analyze”, **Then** the file is stored (identified by filename), the user receives success, and processing is triggered immediately (async).
2. **Given** the user is authenticated, **When** they upload a valid file with “upload and queue”, **Then** the file is stored (identified by filename) and the user receives success; the document remains pending until the next scheduled batch run.
3. **Given** the user has uploaded documents, **When** they request their document list, **Then** they see only their documents with filename and metadata (e.g. name, type, upload time, processing status).
4. **Given** the user uploads a file that is not PDF or Markdown, **When** the request is submitted, **Then** the system rejects it with a clear validation error and does not store the file.

---

### User Story 2 - Process Documents and Build Searchable Knowledge (Priority: P2)

Processing runs in two ways: (1) **Immediately** after an “upload and analyze” action, or (2) **Scheduled batch** for documents that were “upload and queue” (pending). The system analyzes documents using a foundation model (invoked via an endpoint) to produce embeddings, stores them in a vector store for retrieval, and schedules each successfully processed document for deletion from object storage so only the searchable representation remains.

**Why this priority**: Enables RAG; users cannot get answers from document content until analysis and embedding storage are in place.

**Independent Test**: User uploads with “upload and analyze” and verifies processing starts; user uploads with “upload and queue” and verifies document is processed when the scheduled batch runs; in both cases embeddings exist and the original is scheduled for deletion.

**Acceptance Scenarios**:

1. **Given** the user uploaded with “upload and analyze”, **When** the file is stored, **Then** processing is triggered immediately (async) and the document is analyzed and embeddings stored.
2. **Given** one or more documents are in the queue (upload and queue), **When** the scheduled batch runs, **Then** each pending document is analyzed by the foundation model and embeddings are created and stored in the vector store.
3. **Given** embeddings have been created for a document, **When** processing completes, **Then** that document is scheduled for deletion from object storage.
4. **Given** processing fails for a document (e.g. model error, invalid content), **When** the failure is detected, **Then** the system records the failure, does not store partial embeddings for that document, and does not schedule the document for deletion until processing can succeed.

---

### User Story 3 - Ask Questions via RAG (Priority: P3)

An authenticated user submits a natural-language question. The system retrieves relevant content from the vector store (using the stored embeddings) and sends the question plus retrieved context to the foundation model. The user receives an answer grounded in the uploaded and processed documents.

**Why this priority**: Delivers the core value of the product—getting answers from the user’s documents.

**Independent Test**: User uploads and processes at least one document, then submits a question and receives an answer that reflects the document content; can be tested without changing upload or processing flows.

**Acceptance Scenarios**:

1. **Given** at least one document has been processed and embeddings exist, **When** the user submits a question, **Then** the system returns an answer that is grounded in the stored document content.
2. **Given** no documents have been processed (or vector store is empty), **When** the user submits a question, **Then** the system returns a clear message that no knowledge is available (or equivalent) and does not fabricate an answer.
3. **Given** the user is not authenticated, **When** they attempt to submit a RAG query, **Then** the request is rejected with an authentication error.

---

### Edge Cases

- **Large or malformed files**: System enforces a maximum document size of 25 MB per file (primary use case: legal documents; very large bundles must be split before upload). Oversized or corrupted PDF/Markdown is rejected at upload or during processing with a clear error.
- **Duplicate or re-upload**: When the user uploads a file with the same filename as an existing document (same user), the system MUST replace the existing document (overwrite content), re-process it, and refresh embeddings; the user receives confirmation of the update.
- **Partial processing failure**: If some documents in a batch fail analysis, the system continues for others, records failures, and allows retry or inspection of failed items.
- **RAG with no relevant chunks**: When retrieval finds no relevant passages, the system responds with a clear “no relevant content” style response rather than inventing an answer.
- **Concurrent uploads and queries**: Multiple users (or the same user) can upload and query concurrently without corrupting data or returning another user’s documents in RAG results.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow authenticated users to upload documents in PDF and Markdown format and store them in durable object storage. Each document MUST NOT exceed 25 MB (primary use case: legal documents; larger bundles must be split before upload). The document identifier is the **user-scoped filename** (one filename per user). When the user uploads a file with the same filename as an existing document, the system MUST replace the existing document, re-process it, and refresh its embeddings.
- **FR-002**: System MUST expose all operations via a single API surface that is the only interface for clients: upload (with modes “upload and analyze” and “upload and queue”), list, delete document, and RAG query. Processing runs either immediately after “upload and analyze” or via a scheduled batch for queued documents.
- **FR-003**: System MUST authenticate all API requests using OAuth (or equivalent standard) and MUST NOT allow unauthenticated access to upload, list, delete, process, or RAG endpoints.
- **FR-004**: System MUST analyze uploaded documents using a foundation model invoked via an endpoint and MUST store the resulting embeddings in a vector store. Processing MUST be triggerable in two ways: (1) immediately after “upload and analyze”, and (2) via a scheduled batch for documents uploaded with “upload and queue”.
- **FR-005**: System MUST schedule for deletion from object storage each document for which embeddings have been successfully created; deletion may be asynchronous. Embeddings MUST be retained indefinitely until the user explicitly deletes the document (or account); there is no automatic expiry of embeddings.
- **FR-006**: System MUST support RAG queries: given a user question, retrieve relevant content from the vector store and return an answer from the foundation model grounded in that content.
- **FR-007**: System MUST ensure users can access only their own documents and RAG answers are based only on documents they are authorized to use.
- **FR-007a**: System MUST support explicit delete: when the user deletes a document, the system MUST remove the document from object storage (if still present) and MUST remove its embeddings from the vector store so the document no longer contributes to RAG answers.
- **FR-008**: System MUST run as a containerized application and MUST be deployable as a service within a cluster (initial deployment target is a single cluster service).
- **FR-009**: System MUST use only services and capabilities offered by the chosen cloud provider.
- **FR-010**: Continuous integration MUST run via the chosen CI system (build, test, and any pre-deploy checks).
- **FR-011**: System MUST emit structured logs (machine-parseable, with consistent fields such as timestamp, level, message, and request/correlation context) for operational and troubleshooting use.
- **FR-012**: System MUST support observability using open standards (e.g. OpenTelemetry) for metrics, traces, and logs so that monitoring and debugging can integrate with standard tooling.
- **FR-013**: System MUST enforce **per-user rate limits** (throttle by authenticated user; e.g. requests per minute per user). Requests exceeding the limit MUST receive an appropriate response (e.g. HTTP 429) and MUST NOT be processed until the limit window resets.
- **FR-014**: System MUST use **TLS for all API and service traffic** (encryption in transit). Stored data (object storage, vector store, and other persistence) MUST use **encryption at rest** via AWS default mechanisms (e.g. SSE-S3 for S3 and equivalent for other AWS storage).

### Infrastructure Requirements

- **IR-001**: All infrastructure related to this project MUST be defined and provisioned via Terraform (infrastructure as code). Manual or ad-hoc creation of project resources is not permitted.
- **IR-002**: Terraform MUST use the AWS provider version 6 (e.g. `hashicorp/aws` >= 6.0.0).
- **IR-003**: Where Terraform modules are used, they MUST be from the [terraform-aws-modules](https://github.com/terraform-aws-modules) organization authored by Anton Babenko (or community-maintained under that organization). Custom modules may be used only when no suitable terraform-aws-modules module exists; any such exception MUST be documented in the plan.

### Key Entities

- **Document**: A user-provided file (PDF or Markdown) stored in object storage; identified by **filename (document identifier)** — user-scoped (one filename per user; re-upload with same filename replaces). Has owner, format, size, upload time, and processing status (pending, processed, failed, scheduled for deletion).
- **Embedding**: A vector representation of document content produced by the foundation model; stored in the vector store and associated with the source document and owner. Retained indefinitely until the user deletes the document (or account); no automatic expiry.
- **RAG query**: A user question plus retrieved context and the foundation model’s answer; associated with the requesting user and optionally with the documents used for retrieval.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An authenticated user can upload a PDF or Markdown file and receive confirmation (document identified by filename) within 30 seconds under normal load.
- **SC-002**: After processing, users can submit a RAG question and receive an answer grounded in their processed documents within 15 seconds under normal load.
- **SC-003**: Users see only their own documents and receive RAG answers based only on documents they are authorized to access (no cross-tenant or cross-user leakage).
- **SC-004**: When processing completes successfully for a document, that document is scheduled for deletion; no permanent retention of original files in object storage after embeddings exist (except where required for audit or compliance and explicitly documented).
- **SC-005**: Build and test pipeline runs on every relevant change (e.g. push/PR) and completes successfully before merge or deploy.
- **SC-006**: Logs are structured and queryable; observability signals (metrics, traces, logs) are exposed via open standards so operators can monitor and debug with standard tooling.

## Assumptions & Constraints

- **Document type**: Primary use case is legal documents (contracts, agreements, etc.); document size limit (25 MB) is set to accommodate typical single legal documents and moderate multi-exhibit PDFs.
- **Language**: Service implementation will be in Python.
- **Cloud**: All infrastructure and managed services (object storage, vector store, compute, identity) will be AWS offerings.
- **Vector store**: Amazon S3 Vectors for storing and querying embeddings (native vector storage and query in S3; Bedrock integration; cost-optimized; sub-second query performance).
- **Auth**: API access will be authenticated using OAuth (or equivalent) via **Amazon Cognito** (managed user pools and/or OIDC; identity on AWS).
- **Encryption**: TLS for all API and service traffic (in transit); encryption at rest via AWS defaults (e.g. SSE-S3 for S3 and equivalent for other storage).
- **Deployment**: Application will run as containers; initial deployment will be as a single service in an ECS cluster.
- **CI**: Continuous integration will be implemented with GitHub Actions.
- **Observability**: Structured logging and observability will follow open standards (e.g. OpenTelemetry) for metrics, traces, and logs.
- **Scheduled batch**: Processing for "upload and queue" documents runs on a scheduled batch; frequency is **daily** (or configurable). Queued documents remain pending until the next batch run.
- **Infrastructure as Code**: All project infrastructure (e.g. S3, ECS, IAM, networking, Bedrock/S3 Vectors–related resources) will be managed with Terraform using the AWS provider v6; reusable components will use terraform-aws-modules (Anton Babenko) where applicable.
