# Implementation Plan: Document Upload and RAG Service

**Branch**: `001-document-rag-api` | **Date**: 2025-02-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-document-rag-api/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build a containerized API service that lets authenticated users upload legal documents (PDF/Markdown, max 25 MB) to object storage, optionally process them immediately or queue for a **daily (or configurable) scheduled batch**; analyze documents via AWS Bedrock to produce embeddings stored in Amazon S3 Vectors; run RAG queries against that knowledge; schedule originals for deletion after embedding; support explicit document delete. Document identity is the **user-scoped filename** (one filename per user; re-upload with same filename replaces). All operations over a single API with **Amazon Cognito** (OAuth/OIDC), **per-user rate limits**, **TLS and encryption at rest** (AWS defaults), structured logging, and OpenTelemetry observability. Deploy as a single service on ECS; CI with GitHub Actions. **All infrastructure** is defined and provisioned via **Terraform** (AWS provider v6; terraform-aws-modules where modules are used).

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: FastAPI (API), boto3 (AWS SDK), PyPDF2 or pypdf + markdown (text extraction), opentelemetry-api/sdk/exporter-otlp (observability), structlog or equivalent (structured logs)  
**Storage**: Amazon S3 (document objects; SSE-S3 or AWS default encryption at rest), Amazon S3 Vectors (embeddings / RAG); metadata for document list and processing status in DynamoDB or in-app store aligned with S3/vector lifecycle  
**Testing**: pytest, pytest-asyncio, httpx; contract tests for API (including 429 for rate limits), integration tests for upload/process/RAG/delete  
**Target Platform**: Linux containers (ECS Fargate or EC2); AWS  
**Project Type**: web-service (REST API)  
**Performance Goals**: Upload confirmation &lt;30 s, RAG answer &lt;15 s under normal load (per SC-001, SC-002)  
**Constraints**: 25 MB max per document; AWS-only services; OAuth via Cognito for all endpoints; per-user rate limits (e.g. requests/min per user); TLS in transit, encryption at rest (AWS defaults); structured logs + OpenTelemetry  
**Scale/Scope**: Single-tenant per user (isolated by OAuth identity); document and embedding counts scoped per user  
**Infrastructure**: All project infrastructure MUST be defined and provisioned via Terraform. AWS provider version 6 (`hashicorp/aws` &gt;= 6.0.0). Where Terraform modules are used, use [terraform-aws-modules](https://github.com/terraform-aws-modules) (Anton Babenko); custom modules only when no suitable module exists, documented in this plan.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity | Pass | Single API service; no extra projects; YAGNI respected. |
| II. Spec-Driven | Pass | Work derived from spec and this plan. |
| III. Testable | Pass | Plan includes contract and integration tests; red–green–refactor applicable. |
| IV. Traceability | Pass | Branch and specs link to this plan; tasks will reference stories. |
| V. Governance | Pass | No constitution violations. |

## Project Structure

### Documentation (this feature)

```text
specs/001-document-rag-api/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── api/                 # FastAPI app, routes, auth middleware (Cognito), rate limiter
├── services/            # Upload, process, RAG, delete, batch
├── models/              # Document metadata, processing status (domain models)
├── storage/             # S3, vector store, optional DynamoDB abstractions
└── observability/       # Structured logging, OpenTelemetry setup

tests/
├── contract/            # API contract tests (incl. 429 for rate limits)
├── integration/         # Upload, process, RAG, delete flows
└── unit/                # Service and storage unit tests

.github/workflows/       # GitHub Actions CI
Dockerfile               # Container image for ECS

terraform/               # All project infrastructure (AWS provider v6; terraform-aws-modules)
├── main.tf
├── variables.tf
├── outputs.tf
└── modules/             # Only if no terraform-aws-modules equivalent; document exception
```

**Structure Decision**: Single backend service. No separate frontend; API is the only interface. All operations (upload with modes, list, delete, RAG query) live in one FastAPI app; processing runs either inline/async after “upload and analyze” or via a **daily (or configurable)** scheduled batch job for “upload and queue”. Document identifier is the user-scoped filename. Auth via Cognito; per-user rate limits; TLS and encryption at rest per spec. Infrastructure in Terraform (AWS provider v6; terraform-aws-modules).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations; table left empty.
