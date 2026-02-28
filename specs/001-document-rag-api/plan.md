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
**Infrastructure**: All project infrastructure MUST be defined and provisioned via Terraform. Terraform runs in **Terraform Cloud** with state stored there; AWS authentication from Terraform Cloud via **OIDC** (no long-lived AWS keys). AWS provider version 6 (`hashicorp/aws` &gt;= 6.0.0). Where Terraform modules are used, use [terraform-aws-modules](https://github.com/terraform-aws-modules) (Anton Babenko); custom modules only when no suitable module exists, documented in this plan.

### Logging

The application MUST use **structured logging** (e.g. structlog). Log level / verbosity MUST be configurable via:

1. **Command line** (e.g. `--log-level DEBUG`)
2. **Configuration file** (e.g. a `log_level` or `logging.level` setting)

When both are provided, the **command line option takes precedence** over the configuration file.

### Cloud infrastructure phasing

Implementation of cloud infrastructure MUST be separated into **at least two steps**, aligned with what the implementation actually needs at each stage.

- **Step 1 (minimum for initial testing)**: Provision only the resources required for the earliest testable slice. As stated in [LOCAL_TESTING.md](../../docs/LOCAL_TESTING.md), the minimum for initial testing is a **DynamoDB table** (document metadata) and an **S3 bucket** (documents). Terraform tasks MUST reflect this: one task (or coherent set) for “S3 bucket + DynamoDB table” so the team can run and test upload/list/delete against real AWS or LocalStack before adding more infra.
- **Later steps**: Add further infrastructure (Cognito, ECS, S3 Vectors, etc.) as separate tasks, gated by implementation progress—e.g. add Cognito when auth is integrated; add S3 Vectors / Bedrock when processing and RAG are implemented. Tasks in [tasks.md](./tasks.md) SHOULD be ordered so that Terraform work is split accordingly (minimum infra first; then infra required for the next user story or capability).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity | Pass | Single API service; no extra projects; YAGNI respected. |
| II. Spec-Driven | Pass | Work derived from spec and this plan. |
| III. Testable | Pass | Plan includes contract and integration tests; red–green–refactor applicable. |
| IV. Traceability | Pass | Branch and specs link to this plan; tasks will reference stories. |
| V. Governance | Pass | No constitution violations. |
| VI. Shift-Left | Pass | Pre-commit hooks (Terraform + Python) and CI run lint, format, validate, security checks at earliest gate. |
| VII. Documentation | Pass | Plan and specs are documented; code and infra must carry purpose comments per constitution. |

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
.pre-commit-config.yaml  # Pre-commit hooks (Terraform + Python); shift-left per Principle VI
Dockerfile               # Container image for ECS

terraform/               # All project infrastructure (AWS provider v6; terraform-aws-modules)
├── main.tf
├── variables.tf
├── outputs.tf
└── modules/             # Only if no terraform-aws-modules equivalent; document exception
```

**Structure Decision**: Single backend service. No separate frontend; API is the only interface. All operations (upload with modes, list, delete, RAG query) live in one FastAPI app; processing runs either inline/async after “upload and analyze” or via a **daily (or configurable)** scheduled batch job for “upload and queue”. Document identifier is the user-scoped filename. Auth via Cognito; per-user rate limits; TLS and encryption at rest per spec. Infrastructure in Terraform (AWS provider v6; terraform-aws-modules).

### Shift-Left and Quality Gates (Principle VI)

Automated checks run at the **earliest feasible gate**: pre-commit locally and in CI on pull request.

**Pre-commit framework**: Use [pre-commit](https://pre-commit.com/) with config at repository root (`.pre-commit-config.yaml`). CI MUST run the same hooks (e.g. `pre-commit run -a`) so uncommitted-only checks are not bypassed.

**Terraform hooks** (from [antonbabenko/pre-commit-terraform](https://github.com/antonbabenko/pre-commit-terraform)):

| Hook | Purpose |
|------|---------|
| `terraform_fmt` | Reformat `.tf` / `.tfvars` to canonical form. |
| `terraform_validate` | Validate Terraform configuration (syntax and internal consistency). |
| `terraform_tflint` | [TFLint](https://github.com/terraform-linters/tflint) rules for Terraform (best practices, provider rules). |
| `terraform_docs` | Insert/update inputs and outputs docs (e.g. in README) via [terraform-docs](https://terraform-docs.io/). |
| `terraform_checkov` | [Checkov](https://www.checkov.io/) static analysis for security and compliance on Terraform. |

Pin the pre-commit-terraform repo to a released version (e.g. `v1.105.0` or later). Install dependencies per the [pre-commit-terraform docs](https://github.com/antonbabenko/pre-commit-terraform#1-install-dependencies) (Terraform, tflint, terraform-docs, checkov) or use the project's Docker image for CI.

**Python hooks**:

| Hook | Purpose |
|------|---------|
| `ruff` | Lint and format Python (align with existing `pyproject.toml` Ruff config). Run `ruff check` and `ruff format`. |
| `pre-commit-hooks` | Generic hooks: trailing whitespace, end-of-file fixer, check YAML/JSON, detect secrets, etc. |
| Optional: `pytest` | Run unit/contract tests in pre-commit or CI only; prefer CI for speed unless running a fast subset. |

Recommended `.pre-commit-config.yaml` layout: pre-commit-hooks first, then Python (ruff), then Terraform hooks. Document in README or quickstart that contributors run `pre-commit install` and that CI runs `pre-commit run -a`.

### Terraform Cloud

**Execution and state**: Terraform MUST be executed via **Terraform Cloud** (or Terraform Enterprise). State is stored in Terraform Cloud; no local or S3 backend for production state. Use a TFC workspace per environment (e.g. dev, staging, prod) or per feature branch as needed.

**AWS authentication**: Use **OIDC** between Terraform Cloud and AWS so that TFC does not store long-lived AWS access keys. Configure TFC workspace to use a trusted identity provider (e.g. TFC's built-in OIDC) and an IAM OIDC identity provider in the target AWS account; attach an IAM role that TFC can assume. Document the OIDC setup (TFC workspace to AWS account trust, IAM role ARN) in `terraform/README.md` or equivalent.

**Local and CI**: For local `terraform plan` / `terraform validate` and for pre-commit hooks, use local Terraform binary and (if needed) local AWS credentials or env vars; state is not required for `terraform validate` or `terraform_fmt`. CI that applies changes SHOULD use Terraform Cloud's VCS-driven workflow or TFC API so that applies run in TFC with OIDC to AWS.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations; table left empty.
