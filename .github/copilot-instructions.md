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
├── requirements/
│   ├── base.txt
│   └── dev.txt
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
