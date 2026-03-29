from typing import cast
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.dependencies import current_provisioned_user
from app.schemas.auth import AuthenticatedUser
from app.schemas.common import ResponseEnvelope
from app.schemas.job import JobCreate, JobResponse
from app.services.job_service import job_service
from app.worker.jobs import generate_job_embeddings

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
    user: AuthenticatedUser = Depends(current_provisioned_user),
) -> ResponseEnvelope[JobResponse]:
    # current_provisioned_user guarantees internal_user_id is populated.
    internal_user_id = cast(UUID, user.internal_user_id)
    new_job = await job_service.create_job(session, job_in, internal_user_id)
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
    jobs, _total = await job_service.get_jobs(db=db, skip=skip, limit=limit)
    return ResponseEnvelope[list[JobResponse]](
        success=True,
        message="Jobs fetched successfully.",
        data=[JobResponse.model_validate(job) for job in jobs],
    )
