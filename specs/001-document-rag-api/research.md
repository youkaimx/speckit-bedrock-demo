# Research: Document Upload and RAG Service

**Feature**: 001-document-rag-api  
**Date**: 2025-02-26

Decisions and rationale for technical choices. All NEEDS CLARIFICATION from the plan are resolved here.

---

## 1. Language and Runtime

**Decision**: Python 3.12

**Rationale**: Spec and assumptions require Python. 3.12 is current LTS-style and supported on AWS (Lambda, ECS, etc.).

**Alternatives considered**: Python 3.11 (slightly older, also valid); other languages rejected per spec.

---

## 2. API Framework

**Decision**: FastAPI

**Rationale**: Async support, OpenAPI out of the box, type hints, common for Python REST APIs. Fits OAuth middleware and structured response contracts.

**Alternatives considered**: Flask (simpler but less async-native), Starlette (lower-level; FastAPI builds on it).

---

## 3. Object Storage (Documents)

**Decision**: Amazon S3

**Rationale**: Spec requires AWS; S3 is the standard object store. Lifecycle/delete can be used for “scheduled for deletion” after embeddings exist. Prefix or metadata can encode owner and document id.

**Alternatives considered**: None; S3 is the only AWS-native fit for “durable object storage” in spec.

---

## 4. Vector Store and RAG

**Decision**: Amazon S3 Vectors for storing and querying embeddings; Bedrock for embedding model and RAG inference (InvokeModel for embeddings and for answer generation; retrieval from S3 Vectors).

**Rationale**: Spec clarification (Session 2025-02-26) and Assumptions require **Amazon S3 Vectors** as the vector store. S3 Vectors provides native vector storage and query in S3, sub-second query performance, native integration with Amazon Bedrock Knowledge Bases for RAG, and up to ~90% lower cost for storing/uploading/querying vectors ([AWS S3 Vectors](https://aws.amazon.com/s3/features/vectors/)). Same S3 family as document storage; supports (1) immediate processing after “upload and analyze”, (2) scheduled batch for “upload and queue”, (3) explicit delete of document + its embeddings (remove vectors by document id in S3 Vectors). Latency (e.g. ~100 ms warm query) meets success criteria (RAG answer &lt;15 s).

**Alternatives considered**: OpenSearch Serverless vector collection (higher cost, more ops; was prior plan); Bedrock Knowledge Base with S3 data source (simpler but less control over when to process and delete); Aurora pgvector (more ops); third-party vector DB (spec says AWS-only).

---

## 5. Document and Processing Metadata

**Decision**: Store document list and processing status in DynamoDB (or in S3 object metadata + list via S3 + optional small metadata table). Prefer DynamoDB for fast “list my documents” and status (pending / processing / processed / failed) keyed by user id and document id.

**Rationale**: API must return “list of documents with identifiers and metadata (e.g. name, type, upload time, processing status)”. S3 list + metadata can suffice for minimal scope; DynamoDB gives clearer status lifecycle and query by user.

**Alternatives considered**: S3-only (list objects by prefix, metadata on object); RDS (heavier; not required for this scope).

---

## 6. Authentication (OAuth)

**Decision**: Amazon Cognito (OAuth 2.0 / OIDC) as the identity provider for API access.

**Rationale**: Spec requires OAuth; Assumptions say “exact provider to be chosen in design”. Cognito is AWS-native, integrates with API Gateway or FastAPI middleware, and supports standard OAuth2 flows.

**Alternatives considered**: Third-party IdP (Auth0, Okta) — valid but adds vendor and cost; Cognito keeps stack AWS-only per spec. Spec clarification (Session 2025-02-26) confirms **Amazon Cognito**.

---

## 7. Structured Logging

**Decision**: structlog (or equivalent) with JSON output and consistent fields: timestamp, level, message, request_id / correlation_id, and optional user_id (where safe). Emit to stdout for container logs.

**Rationale**: FR-011 requires structured, machine-parseable logs with timestamp, level, message, and request/correlation context. structlog is widely used in Python and supports OpenTelemetry trace id / span id injection.

**Alternatives considered**: Standard logging + JSON formatter; OpenTelemetry logging SDK (can be layered with structlog).

---

## 8. Observability (OpenTelemetry)

**Decision**: OpenTelemetry SDK for Python: auto-instrumentation for HTTP/FastAPI, manual spans for upload/process/RAG/delete; OTLP export for metrics and traces. Logs via structured logs with trace/span ids for correlation.

**Rationale**: FR-012 and SC-006 require observability using open standards (e.g. OpenTelemetry) for metrics, traces, and logs. OTLP allows any backend (e.g. AWS X-Ray, third-party). Correlation of logs and traces via trace_id/span_id satisfies “standard tooling”.

**Alternatives considered**: Vendor-specific SDKs only (would not satisfy “open standards”).

---

## 9. Scheduled Batch (Upload and Queue)

**Decision**: Run a batch job (same codebase, invoked on a schedule) that lists documents in “pending” state for “upload and queue”, calls the same processing pipeline used for “upload and analyze”, then updates status. Schedule via ECS Scheduled Task (or EventBridge + Lambda/ECS) at **daily** (or configurable) interval.

**Rationale**: Spec requires “upload and queue” and “scheduled batch”; daily or configurable (spec clarification Session 2025-02-26). A separate scheduled invocation of the same processing logic keeps code simple and behavior consistent.

**Alternatives considered**: Lambda on schedule (same outcome); in-process cron in API (worse for scaling and ECS lifecycle).

---

## 10. Infrastructure as Code (Terraform)

**Decision**: All project infrastructure defined and provisioned via Terraform. AWS provider version 6 (`hashicorp/aws` >= 6.0.0). Where modules are used, use [terraform-aws-modules](https://github.com/terraform-aws-modules) (Anton Babenko); custom modules only when no suitable module exists, documented in plan.

**Rationale**: Spec clarification and IR-001 to IR-003 require Terraform, AWS provider v6, and terraform-aws-modules for reusable components. Keeps infrastructure reproducible and reviewable.

**Alternatives considered**: Manual/console provisioning (spec forbids); other module sources (spec locks in terraform-aws-modules).

---

## 11. Per-User Rate Limits

**Decision**: Enforce per-user rate limits (throttle by authenticated user; e.g. requests per minute per user). Return HTTP 429 when limit exceeded; do not process until window resets.

**Rationale**: Spec clarification (Session 2025-02-26) and FR-013 require per-user rate limits. Protects service from a single user without requiring global throttling; aligns with user-scoped document access.

**Alternatives considered**: No rate limiting (spec requires); global only (spec requires per-user).

---

## 12. Encryption (TLS and At-Rest)

**Decision**: TLS for all API and service traffic (encryption in transit). Encryption at rest via AWS defaults (e.g. SSE-S3 for S3 and equivalent for other AWS storage).

**Rationale**: Spec clarification (Session 2025-02-26) and FR-014 require TLS in transit and encryption at rest via AWS default mechanisms. Suitable for legal documents and PII without customer-managed keys.

**Alternatives considered**: TLS only (spec requires at-rest); customer-managed KMS keys (defer unless compliance requires).

---

## 13. CI (GitHub Actions)

**Decision**: GitHub Actions workflow on push/PR: install deps, lint, run unit and contract tests; optional integration tests against localstack or test AWS account; build Docker image and optionally push to ECR. No deployment in CI unless explicitly added later.

**Rationale**: Spec and Assumptions require CI via GitHub Actions. Pipeline must run on relevant changes and succeed before merge (SC-005).

**Alternatives considered**: None; spec is explicit.

---

## 14. Deployment (Container / ECS)

**Decision**: Single Docker image (FastAPI app + batch entrypoint or same app with “worker” mode). Run as ECS Fargate service (long-running API) plus optional ECS Scheduled Task for batch, or single service with internal scheduler. Initial target: one ECS service.

**Rationale**: FR-008 and Assumptions require containerized app and deployment as a service in an ECS cluster. Fargate avoids managing servers; batch can be same image, different task definition and schedule.

**Alternatives considered**: ECS EC2 launch type (more control, more ops); Lambda for API (spec says “containerized” and “ECS”, so Lambda not chosen for primary API).
