from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.dependencies import current_active_user
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
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job",
    description="Creates a new job posting in the system."
)
async def create_job(
    job_in: JobCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
    user = Depends(current_active_user)
):
    new_job = await job_service.create_job(session, job_in, user.id)
    background_tasks.add_task(generate_job_embeddings, job_id=new_job.id)
    
    return new_job

@router.get(
    "/",
    response_model=List[JobResponse],
    summary="Get all jobs"
)
async def get_jobs(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_session)
):
    return await job_service.get_jobs(db=db, skip=skip, limit=limit)