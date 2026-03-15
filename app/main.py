from contextlib import asynccontextmanager
import json
from json import JSONDecodeError

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import BaseAppException
from app.core.database import get_async_session
from app.routers import auth, user, job, job_applicant
from app.schemas.common import MessageData, ResponseEnvelope, StatusData

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This is where you would put startup logic
    yield
    # This is where you would put shutdown logic
    

# TODO: in the future Depends(get_query_token)
app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
app.include_router(auth.auth)
app.include_router(user.user)
app.include_router(job.router)
app.include_router(job_applicant.router)


def _is_standard_envelope(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False

    required_keys = {"success", "message", "data", "error", "details"}
    return required_keys.issubset(set(payload.keys()))


@app.middleware("http")
async def wrap_auth_user_route_responses(request: Request, call_next):
    response = await call_next(request)

    route_path = request.url.path
    if not (route_path.startswith("/auth") or route_path.startswith("/users")):
        return response

    if response.status_code == 204:
        return response

    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type.lower():
        return response

    response_body = getattr(response, "body", None)
    if response_body is None:
        return response

    if not response_body:
        payload: object = {}
    else:
        try:
            payload = json.loads(response_body)
        except JSONDecodeError:
            return response

    if _is_standard_envelope(payload):
        return response

    status_code = response.status_code
    is_success = 200 <= status_code < 300

    message = "Request completed successfully." if is_success else "Request failed."
    error_code: str | None = None
    details: dict[str, object] = {}
    data: object | None = payload if is_success else None

    if isinstance(payload, dict):
        detail_field = payload.get("detail")
        if isinstance(detail_field, str):
            message = detail_field
        elif isinstance(detail_field, list):
            message = "Request failed."
            details = {"detail": detail_field}

        if not is_success:
            details = payload
            error_code = "HTTP_ERROR"
    elif isinstance(payload, list):
        if is_success:
            data = payload
            message = "Request completed successfully."
        else:
            details = {"detail": payload}
            error_code = "HTTP_ERROR"

    response_headers = {
        header_name: header_value
        for header_name, header_value in response.headers.items()
        if header_name.lower() != "content-length"
    }

    return JSONResponse(
        status_code=status_code,
        content={
            "success": is_success,
            "message": message,
            "data": data,
            "error": error_code,
            "details": details,
        },
        headers=response_headers,
    )

# Converts custom, application-specific business logic errors (defined by the developer) into the API's standardized JSON error format. 
@app.exception_handler(BaseAppException)
async def handle_base_app_exception(
    _request: Request,
    exc: BaseAppException,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "data": None,
            "error": exc.error_code,
            "details": exc.details,
        },
    )

# Intercepts generic FastAPI web errors (like 404 Not Found or 401 Unauthorized) to ensure they match the API's standard JSON structure rather than FastAPI's default.
@app.exception_handler(HTTPException)
async def handle_http_exception(
    _request: Request,
    exc: HTTPException,
) -> JSONResponse:
    detail_message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": detail_message,
            "data": None,
            "error": "HTTP_ERROR",
            "details": {},
        },
    )

# Formats bad user input errors (like missing fields or incorrect data types caught by Pydantic) into the standard JSON structure, exposing the exact field errors in the details section.
@app.exception_handler(RequestValidationError)
async def handle_validation_exception(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Request validation failed.",
            "data": None,
            "error": "VALIDATION_ERROR",
            "details": {"errors": exc.errors()},
        },
    )

@app.get(
    "/",
    response_model=ResponseEnvelope[MessageData],
    summary="Health greeting",
    description="Returns a standardized root greeting envelope.",
)
def read_root() -> ResponseEnvelope[MessageData]:
    return ResponseEnvelope[MessageData](
        success=True,
        message="Root endpoint reached.",
        data=MessageData(message="Welcome to my FastAPI app!"),
    )

@app.get(
    "/db-test",
    response_model=ResponseEnvelope[StatusData],
    summary="Database connection check",
    description="Returns standardized database connection status envelope.",
)
def test_db(db: AsyncSession = Depends(get_async_session)) -> ResponseEnvelope[StatusData]:
    return ResponseEnvelope[StatusData](
        success=True,
        message="Database connection check completed.",
        data=StatusData(status="Database connection is active"),
    )