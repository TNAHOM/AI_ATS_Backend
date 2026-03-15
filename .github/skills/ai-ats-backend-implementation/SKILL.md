---
name: ai-ats-backend-implementation
description: "Implement and refactor AI ATS backend features in Python FastAPI with PostgreSQL, SQLAlchemy/SQLModel, DTO-first Pydantic responses, strict typing, dependency injection, modular service architecture, standardized error handling, and project-structure compliance. Use when adding endpoints, schemas, services, DB models, migrations, Celery flows, Gemini integrations, vector search, or production backend cleanup."
argument-hint: "Describe the backend feature/refactor you want implemented (endpoint, service, schema, migration, worker, or AI flow)."
user-invocable: true
---

# AI ATS Backend Implementation

## Purpose

Deliver production-grade backend changes for this AI ATS codebase using clean architecture, strict type safety, modular services, and stable API contracts.

## Load These Rules First

1. Read `.github/copilot-instructions.md` before making any implementation decision.
2. Treat those instructions as source-of-truth for stack, architecture, and constraints.
3. If repository reality differs from ideal structure, make changes that respect current codebase patterns while moving toward the defined target architecture.

## Use This Skill When

- Creating or updating FastAPI routers/endpoints.
- Adding DTO schemas for request/response payloads.
- Implementing service-layer business logic.
- Adding database model fields and Alembic migrations.
- Implementing Celery worker pipelines for resume processing.
- Adding Gemini grading, embedding, or vector-search behavior.
- Refactoring code for modularity, typing, and error consistency.

## Non-Negotiable Engineering Rules

- Use dependency injection in routes (`Depends(get_db)`), never direct DB session imports in routers.
- Keep all new route work under `app/routers` (do not migrate to `app/api/endpoints` unless explicitly requested).
- Keep strict boundaries:
  - `models/`: persistence shape only.
  - `schemas/`: input/output DTOs and validation only.
  - `services/`: business logic and external integrations only.
  - routers: orchestration + response mapping only.
- Every endpoint must define `response_model=...` and return schema DTOs, not ORM entities.
- Enforce a strict response envelope for all endpoints (including success and error paths) via typed Pydantic DTOs.
- Use the reusable template at `./assets/response-envelope-dto.template.py` as the default starting point for envelope DTOs.
- Use Pydantic v2 patterns (`model_validate`, typed fields, clear schema contracts).
- Keep strict type hints on all public functions and service methods.
- Never leak raw internal errors to clients.

## Standard Backend Workflow

1. Understand requirement and identify affected layers (router/schema/service/model/worker/migration).
2. Read adjacent files first to match existing conventions.
3. Design DTO contract (`Create`, `Update`, `Response`, paginated list envelopes when needed), starting from `./assets/response-envelope-dto.template.py`.
4. Implement/adjust service logic with typed signatures.
5. Implement router endpoint with `summary`, `description`, `tags`, and `response_model`.
6. Map ORM/domain data to response DTOs using `model_validate()`.
7. Handle errors with standardized app exceptions and user-safe messages.
8. If schema changed, add Alembic migration (never `metadata.create_all`).
9. Run targeted validation (lint/tests/errors) for changed files.
10. Summarize changed files, rationale, and verification results.

## Error Handling Policy

- Prefer explicit guard clauses for validation and business-rule checks.
- Use app-level typed exceptions inheriting from `BaseAppException`.
- Preserve root cause in logs while returning safe client payload format:
  - `{ "error": "ErrorCode", "message": "User-friendly message", "details": {} }`
- Wrap external integration boundaries (Gemini, AWS, DB transaction points) in controlled `try/except` blocks.
- Reject broad `except Exception` blocks entirely.
- Catch only explicit exception types and map each to standardized app exceptions.

## AI ATS-Specific Implementation Rules

### LLM Grading (20/30/50)

Apply strict weighted grading logic:

- 20%: JD Summary + Work Experience vs Candidate Summary + Work Experience.
- 30%: JD Responsibilities vs Candidate Work Experience + Cover Letter (fallback to Work Experience if no Cover Letter).
- 50%: JD Requirements vs full standardized resume profile.
  Output schema must include: `score`, `reasoning`, `missing_skills`.

### Embeddings + Vector Search

- Generate embeddings from standardized JSON profile, not raw resume text.
- Keep vector-related logic isolated in dedicated vector service methods.
- Use pgvector cosine similarity through typed query/service interfaces.

### Worker Parallelism

For resume processing workers:

1. Standardize resume first.
2. Run grading + embedding generation in parallel (`asyncio.gather()` or equivalent sub-tasks).
3. Persist results only when both branches complete successfully.

## Definition of Done Checklist

- Endpoint contracts are DTO-first and stable.
- Every endpoint uses the standardized response envelope DTO.
- Envelope DTO shape is aligned with `./assets/response-envelope-dto.template.py`.
- No ORM model is returned directly from API routes.
- DI usage in routes is correct and consistent.
- Service methods are typed and side effects are explicit.
- Error responses are standardized and safe.
- No broad `except Exception` blocks were introduced.
- Migration exists for DB schema changes.
- File placement stays in current router layout (`app/routers`) unless explicitly asked otherwise.
- Changed code passes targeted validation.

## Suggested Prompt Patterns

- "Implement a new candidate shortlist endpoint using DTO response models and service-layer logic."
- "Refactor this router to return Pydantic response schemas and standardized errors."
- "Add Gemini-based resume grading service with 20/30/50 weighting and typed outputs."
- "Add pgvector cosine similarity search for applicants using standardized profile embeddings."
- "Implement Celery pipeline step to parallelize grading and embedding after standardization."
