# AI ATS Backend API Documentation

This document lists all currently mounted API endpoints in the codebase (`app/main.py`), including method, path, params, request payload, success response, and error response.

## Base Notes

- **App entrypoint:** `app/main.py`
- **Mounted routers:** `/auth`, `/users`, `/jobs`, `/job-applicants`
- **Also available:** `/` and `/db-test`

## Standard Response Shapes

### Success/Error Envelope (used by custom routes)

Most custom endpoints return:

```json
{
  "success": true,
  "message": "Human-readable message",
  "data": {},
  "error": null,
  "details": {}
}
```

Error shape:

```json
{
  "success": false,
  "message": "User-friendly message",
  "data": null,
  "error": "ERROR_CODE",
  "details": {}
}
```

### Validation Error (global)

```json
{
  "success": false,
  "message": "Request validation failed.",
  "data": null,
  "error": "VALIDATION_ERROR",
  "details": {
    "errors": []
  }
}
```

### Auth/User Middleware Wrapping

For routes under `/auth` and `/users`, responses are runtime-wrapped into the same envelope if they are not already in envelope format.

---

## Shared Enums

- `UserType`: `applicant`, `recruiter`, `admin`
- `LocationType`: `remote`, `onsite`, `hybrid`
- `SeniorityStatus`: `intern`, `junior`, `mid`, `senior`
- `ProgressStatus`: `APPLIED`, `SHORTLISTED`, `INTERVIEWING`, `REJECTED`, `HIRED`
- `ApplicationStatus`: `PENDING`, `QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`, `DEAD_LETTER`
- `JobApplicantSortField`: `applied_at`, `name`, `score`
- `SortOrder`: `asc`, `desc`

---

## Health Endpoints

### 1) `GET /`

- **Method:** `GET`
- **Params:** None
- **Request Body:** None
- **Success Response (200):** `ResponseEnvelope[MessageData]`
  - `data.message: string`
- **Error Response:** Standard global error envelope

### 2) `GET /db-test`

- **Method:** `GET`
- **Params:** None
- **Request Body:** None
- **Success Response (200):** `ResponseEnvelope[StatusData]`
  - `data.status: string`
- **Error Response:** Standard global error envelope

---

## Auth Endpoints (`/auth`)

### 3) `GET /auth/authenticated-route`

- **Method:** `GET`
- **Params:** None
- **Request Body:** None
- **Auth:** valid Clerk bearer JWT required (frontend-issued token)
- **Success Response (200):** `ResponseEnvelope[MessageData]`
- **Error Responses:**
  - `401` invalid/missing/expired token
  - `403` inactive or unprovisioned backend user

---

## User Endpoints (`/users`)

### 4) `GET /users/all`

- **Method:** `GET`
- **Query Params:**
  - `skip: int` (default `0`)
  - `limit: int` (default `50`)
  - `user_type: UserType` (optional)
  - `is_verified: bool` (optional)
  - `is_active: bool` (optional)
  - `is_superuser: bool` (optional)
- **Request Body:** None
- **Auth:** superuser required
- **Success Response (200):** `ResponseEnvelope[list[UserRead]]`
- **Error Responses:**
  - `422` validation error
  - `500` with `USER_LIST_FAILED` on DB failure

## Job Endpoints (`/jobs`)

### 5) `POST /jobs/`

- **Method:** `POST`
- **Query/Path Params:** None
- **Request Body:** `JobCreate`
  - `title: str` (required)
  - `description: str` (required)
  - `location: LocationType` (required)
  - `salary: float` (required)
  - `responsibilities: list[str]` (required)
  - `requirements: list[str]` (required)
  - `deadline: datetime` (required, naive datetime expected)
  - `description_embedding: list[float]` (optional)
  - `requirements_embedding: list[float]` (optional)
  - `responsibilities_embedding: list[float]` (optional)
- **Auth:** active user required
- **Success Response (201):** `ResponseEnvelope[JobResponse]`
- **Error Responses:**
  - `422` validation error
  - `500` with `JOB_CREATE_FAILED` on DB failure

### 6) `GET /jobs/`

- **Method:** `GET`
- **Query Params:**
  - `skip: int` (default `0`)
  - `limit: int` (default `50`)
- **Request Body:** None
- **Success Response (200):** `ResponseEnvelope[list[JobResponse]]`
- **Error Responses:**
  - `422` validation error
  - `500` with `JOB_LIST_FAILED` on DB failure

---

## Job Applicant Endpoints (`/job-applicants`)

### 7) `POST /job-applicants/`

- **Method:** `POST`
- **Request Body:** `multipart/form-data`
  - `job_post_id: UUID` (required)
  - `name: str` (required)
  - `email: EmailStr` (required)
  - `phone_number: str` (required)
  - `seniority_level: SeniorityStatus` (optional)
  - `resume: file (PDF)` (required)
- **Success Response (201):** `ResponseEnvelope[JobApplicantResponse]`
- **Error Responses:**
  - `400` `EMPTY_RESUME`, `INVALID_RESUME_FORMAT`
  - `409` `DUPLICATE_APPLICATION`
  - `422` validation error / create constraint failure
  - `502` `RESUME_UPLOAD_FAILED`
  - `500` `JOB_APPLICANT_CREATE_FAILED`

### 8) `POST /job-applicants/{applicant_id}/retry`

- **Method:** `POST`
- **Path Params:**
  - `applicant_id: UUID`
- **Request Body:** None
- **Success Response (202):** `ResponseEnvelope[JobApplicantResponse]`
- **Error Responses:**
  - `404` `APPLICANT_NOT_FOUND`
  - `409` `APPLICANT_NOT_RETRYABLE`, `APPLICANT_ALREADY_PROCESSING`
  - `422` `RESUME_NOT_FOUND`
  - `502` `RESUME_DOWNLOAD_FAILED`
  - `500` `APPLICANT_FETCH_FAILED`, `APPLICANT_RETRY_RESET_FAILED`

### 9) `GET /job-applicants/`

- **Method:** `GET`
- **Query Params:**
  - `page: int` (default `1`, min `1`)
  - `size: int` (default `20`, min `1`, max `100`)
  - `job_post_id: UUID` (optional)
  - `progress_status: ProgressStatus` (optional)
  - `seniority_level: SeniorityStatus` (optional)
  - `application_status: ApplicationStatus` (optional)
  - `min_score: float` (optional, 0..10)
  - `max_score: float` (optional, 0..10)
  - `sort_by: JobApplicantSortField` (default `applied_at`)
  - `sort_order: SortOrder` (default `desc`)
- **Auth:** active user required
- **Success Response (200):** `ResponseEnvelope[PaginatedPayload[JobApplicantResponse]]`
  - `data.items`, `data.total`, `data.page`, `data.size`
- **Error Responses:**
  - `400` `INVALID_SORT_FIELD`
  - `422` validation error
  - `500` `JOB_APPLICANT_LIST_FAILED`

### 10) `GET /job-applicants/vector-search/{job_post_id}`

- **Method:** `GET`
- **Path Params:**
  - `job_post_id: UUID`
- **Query Params:**
  - `top_k: int` (default `10`, min `1`, max `100`)
- **Auth:** active user required
- **Success Response (200):** `ResponseEnvelope[JobApplicantVectorSearchData]`
  - `data.job_post_id`
  - `data.total_candidates`
  - `data.ranked_applicants[]` with:
    - `applicant: JobApplicantResponse`
    - `similarity_score: float`
- **Error Responses:**
  - `400` `INVALID_TOP_K`
  - `404` `JOB_NOT_FOUND`
  - `409` `JOB_EMBEDDINGS_NOT_READY`
  - `422` validation error
  - `500` `VECTOR_SEARCH_FAILED`

### 11) `GET /job-applicants/{applicant_id}`

- **Method:** `GET`
- **Path Params:**
  - `applicant_id: UUID`
- **Request Body:** None
- **Auth:** active user required
- **Success Response (200):** `ResponseEnvelope[JobApplicantResponse]`
- **Error Responses:**
  - `404` `JOB_APPLICANT_NOT_FOUND`
  - `422` validation error
  - `500` `JOB_APPLICANT_FETCH_FAILED`

---

## Key DTO References

- `UserCreate`, `UserRead`, `UserUpdate` -> `app/schemas/user.py`
- `JobCreate`, `JobResponse` -> `app/schemas/job.py`
- `JobApplicantCreate`, `JobApplicantResponse`, vector/pagination DTOs -> `app/schemas/job_applicant.py`
- `ResponseEnvelope`, `PaginatedPayload` -> `app/schemas/common.py`
- Standard app exception format -> `app/core/exceptions.py` + handlers in `app/main.py`

---

## Source of Truth

This document is aligned to runtime router mounting and OpenAPI generation from:

- `app/main.py`
- `app/routers/auth.py`
- `app/routers/user.py`
- `app/routers/job.py`
- `app/routers/job_applicant.py`
