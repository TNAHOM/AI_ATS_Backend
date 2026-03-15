---
name: ATS Backend Enforcement Rules
description: "Use when implementing or refactoring backend Python code in this ATS repository. Enforces strict API response envelope, current router layout under app/routers, and explicit exception handling without broad except Exception blocks."
applyTo:
  - "app/**/*.py"
  - "migrations/**/*.py"
---

# ATS Backend Enforcement Rules

Apply these rules to all matching backend Python files.

## Mandatory Rules

- Enforce a strict response envelope for all API endpoints.
- Keep new and modified route modules under `app/routers`.
- Reject broad `except Exception` blocks entirely.

## API Contract Rules

- Every FastAPI route must declare a typed `response_model`.
- All route outputs must return DTOs from `app/schemas`, not ORM models.
- Response payloads must use a stable envelope schema pattern consistently across endpoints.
- Use `./skills/ai-ats-backend-implementation/assets/response-envelope-dto.template.py` as the default template source for envelope DTO design.

## Routing and Structure Rules

- Keep router implementation in `app/routers` for all new work.
- Do not create or migrate route files to `app/api/endpoints` unless explicitly requested.
- Preserve existing module boundaries (`routers` -> `services` -> `models/schemas`).

## Exception Handling Rules

- Catch explicit exception types only.
- Use standardized app exceptions for client-facing errors.
- Never introduce `except Exception` in backend code.
- If an unknown failure path exists, handle through explicit domain/integration exception classes and safe error mapping.

## Review Checklist Before Finalizing Changes

- `response_model` exists on every changed endpoint.
- Response envelope is present and consistent.
- Envelope schema design is aligned with `./skills/ai-ats-backend-implementation/assets/response-envelope-dto.template.py`.
- Changed/added routes remain under `app/routers`.
- No `except Exception` was introduced.
