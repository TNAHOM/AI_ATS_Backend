# AI ATS Backend MVP Launch Checklist

> Scope: practical pre-launch work based on current codebase state, recent commits, and project instructions.

## Security

- [ ] Enforce strict CORS allowlist so only your frontend domains can call the API in production.
- [ ] Add API rate limiting on auth and upload endpoints to reduce brute-force and abuse risk.
- [ ] Replace password-reset token `print` logging with real email delivery and masked audit logs.
- [ ] Add role/permission guards (e.g., recruiter/admin only) for job creation and applicant management routes.
- [ ] Validate upload MIME type + size + extension and reject unsafe files before S3 upload.
- [ ] Add malware scanning for uploaded resumes (e.g., ClamAV or cloud-native scan workflow).
- [ ] Rotate and securely store secrets in a managed secret store (AWS Secrets Manager/SSM), not only `.env`.
- [ ] Add authentication hardening (short JWT lifetime, refresh strategy, token revocation/blacklist policy).
- [ ] Add production security headers and trusted host checks at app/gateway level.
- [ ] Add structured security audit logging for login, password reset, and failed authorization events.

## Features

- [ ] Implement and test the strict 20/30/50 grading rubric in AI scoring to align with ATS requirements.
- [x] Run resume grading and embedding in parallel in worker flow (`asyncio.gather`) to reduce processing latency.
- [x] Add a dedicated vector search endpoint/service for ranking applicants by cosine similarity.
- [ ] Add pagination/filter/sort on applicant listing endpoints for recruiter usability at scale.
- [ ] Add update endpoints for applicants and normalize TODOs in applicant schema/flow.
- [ ] Add job-applicant processing retries with max-attempt policy and dead-letter handling.
- [ ] Add idempotency protection for applicant processing to avoid duplicate analysis on retries.
- [ ] Add health/readiness checks for DB, AI provider, and storage dependencies.
- [ ] Add a minimal recruiter dashboard API payload (status counts + top candidates per job).
- [ ] Expand API docs quality (summary/description/examples) consistently across all routes.

## Additional Libraries / APIs / Packages to Integrate

- [ ] Build and pin a complete `requirements.txt` from actual imports to make deployments reproducible.
- [ ] Add `celery` + `redis` to move heavy processing from FastAPI `BackgroundTasks` to durable workers.
- [ ] Add `uvicorn[standard]` + `gunicorn` for production ASGI serving and worker management.
- [ ] Add `psycopg[binary]` (or `asyncpg` stack consistency) and pin DB driver versions explicitly.
- [ ] Add `python-multipart` for stable file upload parsing in FastAPI.
- [ ] Add `email-validator` (already implied by `EmailStr`) as an explicit dependency.
- [ ] Add `slowapi` (or equivalent) for request throttling and abuse protection.
- [ ] Add `sentry-sdk[fastapi]` for production error monitoring and release tracking.
- [ ] Add `prometheus-fastapi-instrumentator` for metrics and alertable API observability.
- [ ] Add `pytest` + `pytest-asyncio` + `httpx` for async API tests and regression coverage.
- [ ] Add `ruff` + `mypy` + `pre-commit` for lint/type gates before merge.
- [ ] Add `google-genai`, `boto3`, `tenacity`, `sqlmodel`, `pgvector`, `alembic`, and `fastapi-users` as pinned runtime dependencies.

## Launch Sequence (Suggested)

- [ ] Security hardening first (CORS, rate limits, auth/logging, file safety).
- [ ] Worker architecture second (Celery + Redis + retry/idempotency + parallel AI tasks).
- [ ] Feature completion third (grading quality, vector search, recruiter list experience).
- [ ] Reliability gates last (tests, observability, pinned dependencies, deployment checks).
