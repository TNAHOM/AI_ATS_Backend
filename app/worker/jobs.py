import logging
import uuid

from app.worker.utils import task_monitor
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
    async with task_monitor(Job, job_id) as (job, session):
        if not job:
            return
        # 1. Generate Embeddings
        job.description_embedding = await ai_service.get_embedding(job.description)
        job.requirements_embedding = await ai_service.get_embedding("\n".join(job.requirements))
        job.responsibilities_embedding = await ai_service.get_embedding("\n".join(job.responsibilities))
