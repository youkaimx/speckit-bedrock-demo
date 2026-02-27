<!--
Sync Impact Report
- Version change: 1.0.0 → 1.1.0 (new principle: Shift-Left)
- Modified principles: none
- Added sections: Core Principles VI. Shift-Left
- Removed sections: none
- Templates: plan-template.md ✅ (Constitution Check gate reads constitution); spec-template.md ✅ (scope unchanged); tasks-template.md ✅ (task types compatible)
- Commands: .cursor/commands/*.md ✅ (no updates required)
- Follow-up TODOs: none
-->

# Speckit Bedrock Demo Constitution

## Core Principles

### I. Simplicity

Prefer the simplest approach that meets requirements. Avoid unnecessary abstraction or
complexity. YAGNI: do not add capability until it is required by a spec or user story.

**Rationale**: Keeps the codebase maintainable and reduces risk of over-engineering.

### II. Spec-Driven

Features MUST be specified before implementation. Use `.specify` workflows: specs in
`specs/`, plans in `plan.md`, tasks in `tasks.md`. New work SHOULD originate from a
feature spec or an approved amendment.

**Rationale**: Ensures shared understanding and traceability from idea to implementation.

### III. Testable

Changes MUST be verifiable. When a feature spec or plan calls for tests, tests MUST be
written and MUST fail before implementation (red–green–refactor). Prefer automated
checks over manual-only validation.

**Rationale**: Reduces regressions and documents intended behavior.

### IV. Traceability

Work SHOULD link to specs, plans, and tasks where applicable. Branch names, commit
messages, and task IDs SHOULD reference the feature or story they implement.

**Rationale**: Makes it possible to understand why code exists and what it fulfills.

### V. Governance

This constitution is the source of project rules. Amendments require documentation,
version bump, and propagation to dependent templates. All PRs and reviews MUST verify
compliance with these principles; violations MUST be justified or fixed.

**Rationale**: Single source of truth for how we build and change the project.

### VI. Shift-Left

Quality, security, and correctness MUST be addressed as early as possible in the
lifecycle. Automated checks (lint, tests, security) MUST run at the earliest
feasible gate (e.g. pre-commit or CI on pull request). Where the spec or plan
calls for tests, tests MUST be defined or run before or alongside implementation
(see Principle III). Design and spec phases SHOULD surface defects and
non-functional requirements so they are fixed left of deployment.

**Rationale**: Catching issues early reduces cost and risk; shift-left practices
align with Testable and Spec-Driven principles.

## Constraints

- Technology choices MUST align with the implementation plan for each feature.
- No new mandatory tooling or process beyond what is in the spec/plan unless justified
  and documented in the constitution or plan.

## Workflow

- Use `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`, and related commands as the
  default path for new features.
- Code review MUST check alignment with the constitution; complexity MUST be justified.

## Governance

- This constitution supersedes ad-hoc practices when they conflict.
- Amendments: document change, update version (semantic: MAJOR = breaking principle
  change, MINOR = new principle/section, PATCH = clarifications), set Last Amended date,
  and propagate to dependent templates.
- Compliance: re-check at plan Phase 0 and after Phase 1; flag violations in the
  Constitution Check section of the plan.

**Version**: 1.1.0 | **Ratified**: 2025-02-26 | **Last Amended**: 2026-02-26
