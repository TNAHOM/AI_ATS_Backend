import logging
import uuid
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.job import Job
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)

async def generate_job_embeddings(job_id: uuid.UUID):
    """
    Background task to generate embeddings for a job.
    Manages its own DB session to avoid 'Session Closed' errors.
    """
    logger.info(f"Starting background embedding generation for Job {job_id}")
    
    # CRITICAL: Open a NEW session for the background task
    async with async_session_maker() as session:
        try:
            # 1. Fetch the job
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            
            if not job:
                logger.error(f"Job {job_id} not found in background task.")
                return

            # 2. Generate Embeddings (await to respect rate limits, can parallelize if needed)
            # We join list fields with newlines to create a cohesive semantic block
            description_vector = await ai_service.get_embedding(job.description, is_query=False)
            
            requirements_text = "\n".join(job.requirements)
            requirements_vector = await ai_service.get_embedding(requirements_text, is_query=False)
            
            responsibilities_text = "\n".join(job.responsibilities)
            responsibilities_vector = await ai_service.get_embedding(responsibilities_text, is_query=False)

            # 3. Update the Job
            job.description_embedding = description_vector
            job.requirements_embedding = requirements_vector
            job.responsibilities_embedding = responsibilities_vector

            session.add(job)
            await session.commit()
            logger.info(f"Successfully added embeddings to Job {job_id}")

        except Exception as e:
            logger.exception(f"Failed to process embeddings for Job {job_id}: {e}")
            # Optional: Add logic here to mark the job as "embedding_failed" in DB