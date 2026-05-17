import logging
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.exceptions import BaseAppException
from app.dependencies import current_active_user
from app.schemas.auth import AuthenticatedUser
from app.schemas.common import ResponseEnvelope, ResponseMeta
from app.schemas.job import JobCreate, JobResponse
from app.services.job_service import job_service
from app.worker.jobs import generate_job_embeddings

logger = logging.getLogger(__name__)

# Define prefix and tags ONCE here
router = APIRouter(
    prefix="/jobs",
    tags=["jobs"]
)


@router.post(
    "/",
    response_model=ResponseEnvelope[JobResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job",
    description="Creates a new job posting in the system."
)
async def create_job(
    job_in: JobCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
    user: AuthenticatedUser = Depends(current_active_user),
) -> ResponseEnvelope[JobResponse]:
    logger.info(
        f"User {user.internal_user_id} is creating a new job: {job_in.title}")
    new_job = await job_service.create_job(session, job_in, user.internal_user_id)
    background_tasks.add_task(generate_job_embeddings, job_id=new_job.id)

    return ResponseEnvelope[JobResponse](
        success=True,
        message="Job created successfully.",
        data=JobResponse.model_validate(new_job),
    )


@router.get(
    "/",
    response_model=ResponseEnvelope[list[JobResponse]],
    summary="Get all jobs",
    description="Returns all jobs using a standardized response envelope."
)
async def get_jobs(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_session)
) -> ResponseEnvelope[list[JobResponse]]:
    logger.info(f"Fetching jobs with skip={skip}, limit={limit}")
    jobs, total_count = await job_service.get_jobs(db=db, skip=skip, limit=limit)
    return ResponseEnvelope[list[JobResponse]](
        success=True,
        message="Jobs fetched successfully.",
        data=[JobResponse.model_validate(job) for job in jobs],
        meta=ResponseMeta(
            total=total_count,
            skip=skip,
            limit=limit
        )
    )


@router.get(
    "/{job_id}",
    response_model=ResponseEnvelope[JobResponse],
    summary="Get job by ID",
    description="Returns a specific job by its ID."
)
async def get_job_by_id(
    job_id: UUID,
    db: AsyncSession = Depends(get_async_session)
) -> ResponseEnvelope[JobResponse]:
    logger.info(f"Fetching job with ID: {job_id}")
    job = await job_service.get_job_by_id(db=db, job_id=job_id)
    if not job:
        raise BaseAppException(
            error_code="JOB_NOT_FOUND",
            message="Job not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return ResponseEnvelope[JobResponse](
        success=True,
        message="Job fetched successfully.",
        data=JobResponse.model_validate(job),
    )
