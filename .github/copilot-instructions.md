````markdown
# AI-Powered ATS Backend Instructions

You are an Expert Senior Python Backend Engineer. You are building the production-ready backend for an AI-powered Applicant Tracking System (ATS).

## Core Tech Stack

- **Framework:** FastAPI (Async)
- **Database:** PostgreSQL + `pgvector`
- **ORM:** SQLModel (Combines Pydantic & SQLAlchemy) or SQLAlchemy 2.0+
- **Auth:** fastapi-users (JWT)
- **Async Tasks:** Celery + Redis
- **Cloud:** AWS (Boto3 for S3 & Textract)
- **AI:** Google Gemini 2.5 Flash Lite

## STRICT Project Structure

You must place files strictly according to this hierarchy. Do not create flat structures.

```text
AI_ATS_Backend/
├── app/
│   ├── api/
│   │   ├── endpoints/
│   │   │   ├── auth.py
│   │   │   ├── candidates.py
│   │   │   └── jobs.py
│   │   └── api.py (Router aggregator)
│   ├── core/
│   │   ├── config.py (Pydantic Settings, Env Vars)
│   │   ├── security.py
│   │   ├── database.py (SessionLocal, engine)
│   │   └── logging.py
│   ├── models/ (SQLAlchemy/SQLModel DB Tables)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── candidate.py
│   │   └── job.py
│   ├── schemas/ (Pydantic Data Transfer Objects)
│   │   ├── __init__.py
│   │   ├── candidate_schema.py
│   │   └── job_schema.py
│   ├── services/ (Business Logic & External Integrations)
│   │   ├── llm_service.py (Gemini Logic)
│   │   ├── aws_service.py (S3 & Textract)
│   │   └── vector_service.py (Embeddings)
│   ├── worker/
│   │   └── celery_app.py
│   ├── main.py (App entry point)
│   └── dependencies.py (DI: get_db, get_current_user)
├── migrations/ (Alembic)
├── requirements.txt
└── README.md
```
````

## Coding Standards & Conventions

### 1. Dependency Injection (DI)

- Never import the database session directly in routers.
- **Strict Rule:** Always use `db: Session = Depends(get_db)` in route functions.
- Services should accept the `db` session as an argument.

### 2. Pydantic & Type Safety

- Use **Pydantic V2** (`model_validate`, `ConfigDict`).
- strict Type Hinting is mandatory (e.g., `def process(x: int) -> str:`).
- **Separation of Concerns:**
  - `schemas/`: Input/Output validation only.
  - `models/`: Database tables only.
  - Never return a DB Model directly; convert it to a Pydantic Schema.

### 2.1 Response Models (Mandatory, Pydantic-First)

- You must **heavily use Pydantic response models** for all API responses.
- Every route must define `response_model=...` in the FastAPI decorator.
- Always return a schema from `app/schemas/`, not ORM entities.
- For list responses, use typed containers (e.g., `list[CandidateResponse]`).
- For create/update flows, define dedicated schemas (`Create`, `Update`, `Response`) instead of reusing one model for all operations.
- Use `model_validate()` to map DB objects into response schemas.
- For nested output, compose response DTOs explicitly (do not expose raw relationship objects implicitly).
- Standardize envelope responses for metadata where needed (e.g., pagination: `items`, `total`, `page`, `size`).
- Keep response payloads stable and minimal; avoid leaking internal fields (password hashes, internal IDs not meant for clients, audit fields unless required).
- Services may return domain data, but API endpoints are responsible for returning final Pydantic response DTOs.

### 2.2 Standardized Error Handling
- All custom exceptions must inherit from a `BaseAppException`.
- Use a global FastAPI exception handler to return a standardized JSON structure: `{"error": "ErrorCode", "message": "User-friendly message", "details": {}}`.
- Never leak raw stack traces or database errors (e.g., integrity errors) to the client.

### 2.3 Documentation Metadata
- Every endpoint must include a `summary` and `description` in the FastAPI decorator.
- Use `tags` to group endpoints logically (e.g., `tags=["Candidates"]`) for a clean Swagger UI.
- Use Pydantic `Field` with `examples` and `description` to document schema attributes.

### 2.4 Alembic Migration Workflow
- **Strict Rule:** Never use `SQLModel.metadata.create_all()`.
- All database schema changes must be performed via Alembic migrations.
- Migration scripts must be descriptive and checked for accuracy before being committed (e.g., `alembic revision --autogenerate -m "add_vector_column_to_candidate"`).

### 3. Parallel Processing (Performance)

- In the Celery worker, after the resume is standardized into JSON, **you must execute Grading and Embedding in parallel**.
- Use `asyncio.gather()` if running in an async context, or spawn sub-tasks.
- **Flow:**
  1.  `Standardize Resume` (Blocking/Await).
  2.  `asyncio.gather( task_grade_resume(), task_generate_embeddings() )`
  3.  Save results to DB once both complete.

### 4. Configuration

- All secrets (API Keys, DB URL) must be loaded from `app.core.config.py` using `pydantic-settings`. Never hardcode strings.

## Logic Implementation Details

### LLM Grading Logic (20/30/50 Rule)

When implementing `services/llm_service.py`, the grading prompt must strictly follow:

1.  **20% Score:** Job Description (Summary + Work Exp) VS Candidate (Summary + Work Exp).
2.  **30% Score:** JD Responsibilities VS Candidate (Work Exp + Cover Letter). _Note: If Cover Letter is missing, compare against Work Exp only._
3.  **50% Score:** JD Requirements VS Whole Resume.
4.  **Output:** JSON containing `score`, `reasoning`, and `missing_skills`.

### Vector Search

- Use `pgvector` in `models/candidate.py`.
- Store embeddings of the **Standardized JSON Profile** (not raw text).
- Create a specific service method in `services/vector_service.py` to handle cosine similarity queries.

```

```

## Copilot Coding Agent Task Quality

To improve output quality when using GitHub Copilot coding agent, use these rules for every assigned task:

- Start with well-scoped issues:
  - clear problem statement
  - acceptance criteria
  - expected files or areas to change when known
- If requirements are ambiguous or missing, ask targeted clarification questions before implementing.
- Prefer small, focused PRs over broad multi-feature changes.
- Always preserve existing architecture and naming conventions in this repository.

### Required context-loading order

When starting work, load guidance in this order:
1. `.github/copilot-instructions.md` (this file)
2. `.github/instructions/**/*.instructions.md`
3. `.github/skills/**/SKILL.md`
4. Relevant source files in `app/` and `migrations/`

If guidance conflicts, prioritize:
1. Repository instructions (`.github/copilot-instructions.md`)
2. Path-specific instruction files
3. Skill guidance

### Clarification protocol

If the answer is not available from:
- `.github/agents` configuration provided by maintainers,
- `.github/instructions`,
- `.github/skills`,
- or this `copilot-instructions.md`,

then ask concise clarification questions and wait for user confirmation before implementing uncertain behavior.

### Validation expectations

- Validate changed Python files for syntax correctness (`python -m compileall app`).
- Run repository tests/linters if configured in the environment.
- If dependencies are missing (for example, `pytest` not installed), report that clearly and continue with available validations.
