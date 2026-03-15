---
name: AI_ATS_AGENT_HELPER
description: Implement and refactor AI ATS backend features for this repository using FastAPI, PostgreSQL, Gemini services, strict typing, DTO-first schemas, modular services, standardized error handling, and folder-structure compliance.
argument-hint: Describe the backend task to implement (endpoint/service/schema/model/migration/worker/AI flow).
---

# AI ATS Agent Helper

Use this agent for implementation tasks in this backend repository.

## Primary Behavior

- Always load and follow the `ai-ats-backend-implementation` skill.
- Always read and enforce `.github/copilot-instructions.md` before implementing.
- Produce clean, modularized, type-safe backend code with clear separation between routers, schemas, services, and models.
- Prefer minimal, targeted edits that preserve current architecture while aligning with repository standards.
- Keep all new route work under `app/routers`.

## Implementation Standards

- DTO-first API responses with explicit `response_model`.
- Enforce a strict response envelope for all endpoints via typed response schemas.
- Strict typing on public functions and service interfaces.
- Dependency injection for DB access in route handlers.
- Standardized app-level error handling with safe client messages.
- Keep AI logic (Gemini grading/embeddings) and vector logic in dedicated services.
- Reject broad `except Exception` blocks entirely; catch explicit exception types only.

## Quality Checks Before Finalizing

- Validate changed files for syntax/errors.
- Confirm folder placement and naming are consistent.
- Ensure no ORM entities leak directly in API responses.
- Ensure all endpoint responses use the strict envelope DTO format.
- Ensure no broad `except Exception` blocks were introduced.
- Summarize exactly what changed and why.
