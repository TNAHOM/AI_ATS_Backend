import logging
from uuid import UUID
from typing import Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import BaseAppException
from app.models.job import Job
from app.schemas.job import JobCreate
logger = logging.getLogger(__name__)

class JobService:
    async def create_job(self, db: AsyncSession, job_data: JobCreate, user_id: UUID) -> Job:
        try:
            db_job = Job(**job_data.model_dump(), user_id=user_id)
            
            db.add(db_job)
            await db.commit()
            await db.refresh(db_job)
            
            logger.info(f"User {user_id} created Job {db_job.id}")
            return db_job
            
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error while creating job: {e}")
            raise BaseAppException(
                error_code="JOB_CREATE_FAILED",
                message="Failed to create job posting.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    async def get_jobs(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[Job], int]:
        try:
            query = select(Job).offset(skip).limit(limit)
            result = await db.execute(query)
            jobs = result.scalars().all()

            count_query = select(func.count()).select_from(Job)
            count_result = await db.execute(count_query)
            total = int(count_result.scalar_one())

            return jobs, total
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch jobs: {e}")
            raise BaseAppException(
                error_code="JOB_LIST_FAILED",
                message="Could not retrieve jobs.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

job_service = JobService()