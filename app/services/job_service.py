import logging
from uuid import UUID
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create job posting."
            )

    async def get_jobs(self, db: AsyncSession, skip: int = 0, limit: int = 50) -> Sequence[Job]:
        try:
            # SQLAlchemy 2.0 Async Syntax
            query = select(Job).offset(skip).limit(limit)
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to fetch jobs: {e}")
            raise HTTPException(status_code=500, detail="Could not retrieve jobs.")

job_service = JobService()