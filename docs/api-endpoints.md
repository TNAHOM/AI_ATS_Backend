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

### 3) `POST /auth/jwt/login`

- **Method:** `POST`
- **Params:** None
- **Request Body:** `application/x-www-form-urlencoded`
  - `username` (required)
  - `password` (required)
  - `grant_type` (optional, pattern `password`)
  - `scope` (optional)
  - `client_id` (optional)
  - `client_secret` (optional)
- **Success Response (200):**
  - OpenAPI schema: `BearerResponse` (`access_token`, `token_type`)
  - Runtime response on `/auth`: wrapped into standard envelope
- **Error Responses:**
  - `400` invalid credentials (`ErrorModel` in OpenAPI, wrapped at runtime)
  - `422` validation error

### 4) `POST /auth/jwt/logout`

- **Method:** `POST`
- **Params:** None
- **Request Body:** None
- **Success Response (200):** empty object (wrapped at runtime)
- **Error Responses:**
  - `401` unauthorized

### 5) `POST /auth/register`

- **Method:** `POST`
- **Params:** None
- **Request Body:** `UserCreate`
  - `email` (required)
  - `password` (required)
  - `user_type` (required, `UserType`)
  - `first_name` (required)
  - `last_name` (required)
  - `phone_number` (required)
  - `is_active` (optional)
  - `is_superuser` (optional)
  - `is_verified` (optional)
- **Success Response (201):**
  - OpenAPI schema: `UserRead`
  - Runtime response on `/auth`: wrapped into standard envelope
- **Error Responses:**
  - `400` business/auth error
  - `422` validation error

### 6) `POST /auth/verify/request-verify-token`

- **Method:** `POST`
- **Params:** None
- **Request Body:**
  - `email` (required)
- **Success Response (202):** empty object (wrapped at runtime)
- **Error Responses:**
  - `422` validation error

### 7) `POST /auth/verify/verify`

- **Method:** `POST`
- **Params:** None
- **Request Body:**
  - `token` (required)
- **Success Response (200):**
  - OpenAPI schema: `UserRead`
  - Runtime response on `/auth`: wrapped into standard envelope
- **Error Responses:**
  - `400` invalid/expired token
  - `422` validation error

### 8) `POST /auth/auth/forgot-password`

- **Method:** `POST`
- **Params:** None
- **Request Body:**
  - `email` (required)
- **Success Response (202):** empty object (wrapped at runtime)
- **Error Responses:**
  - `422` validation error

### 9) `POST /auth/auth/reset-password`

- **Method:** `POST`
- **Params:** None
- **Request Body:**
  - `token` (required)
  - `password` (required)
- **Success Response (200):** empty object (wrapped at runtime)
- **Error Responses:**
  - `400` invalid token/password policy issue
  - `422` validation error

### 10) `GET /auth/authenticated-route`

- **Method:** `GET`
- **Params:** None
- **Request Body:** None
- **Auth:** active user required
- **Success Response (200):** `ResponseEnvelope[MessageData]`
- **Error Responses:**
  - `401` unauthorized

---

## User Endpoints (`/users`)

### 11) `GET /users/all`

- **Method:** `GET`
- **Query Params:**
  - `skip: int` (default `0`)
  - `limit: int` (default `50`)
  - `user_type: UserType` (optional)
  - `is_verified: bool` (optional)
  - `is_active: bool` (optional)
  - `is_superuser: bool` (optional)
- **Request Body:** None
- **Auth:** active user required
- **Success Response (200):** `ResponseEnvelope[list[UserRead]]`
- **Error Responses:**
  - `422` validation error
  - `500` with `USER_LIST_FAILED` on DB failure

### 12) `GET /users/me`

- **Method:** `GET`
- **Params:** None
- **Request Body:** None
- **Auth:** active user required
- **Success Response (200):**
  - OpenAPI schema: `UserRead`
  - Runtime response on `/users`: wrapped into standard envelope
- **Error Responses:**
  - `401` unauthorized

### 13) `PATCH /users/me`

- **Method:** `PATCH`
- **Params:** None
- **Request Body:** `UserUpdate`
  - optional fields: `password`, `email`, `is_active`, `is_superuser`, `is_verified`
  - required in current schema: `user_type`, `first_name`, `last_name`, `phone_number`
- **Success Response (200):**
  - OpenAPI schema: `UserRead`
  - Runtime response on `/users`: wrapped into standard envelope
- **Error Responses:**
  - `400` update/auth error
  - `401` unauthorized
  - `422` validation error

### 14) `GET /users/{id}`

- **Method:** `GET`
- **Path Params:**
  - `id: UUID`
- **Request Body:** None
- **Auth:** active user (permissions enforced by fastapi-users)
- **Success Response (200):**
  - OpenAPI schema: `UserRead`
  - Runtime response on `/users`: wrapped into standard envelope
- **Error Responses:**
  - `401` unauthorized
  - `403` forbidden
  - `404` user not found
  - `422` validation error

### 15) `PATCH /users/{id}`

- **Method:** `PATCH`
- **Path Params:**
  - `id: UUID`
- **Request Body:** `UserUpdate`
- **Auth:** active user (permissions enforced by fastapi-users)
- **Success Response (200):**
  - OpenAPI schema: `UserRead`
  - Runtime response on `/users`: wrapped into standard envelope
- **Error Responses:**
  - `400` update/auth error
  - `401` unauthorized
  - `403` forbidden
  - `404` user not found
  - `422` validation error

### 16) `DELETE /users/{id}`

- **Method:** `DELETE`
- **Path Params:**
  - `id: UUID`
- **Request Body:** None
- **Auth:** active user (permissions enforced by fastapi-users)
- **Success Response (204):** no content
- **Error Responses:**
  - `401` unauthorized
  - `403` forbidden
  - `404` user not found
  - `422` validation error

---

## Job Endpoints (`/jobs`)

### 17) `POST /jobs/`

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

### 18) `GET /jobs/`

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

### 19) `POST /job-applicants/`

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

### 20) `POST /job-applicants/{applicant_id}/retry`

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

### 21) `GET /job-applicants/`

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

### 22) `GET /job-applicants/vector-search/{job_post_id}`

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

### 23) `GET /job-applicants/{applicant_id}`

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
