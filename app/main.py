from contextlib import asynccontextmanager

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