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
        if not job or not session:
            logger.warning(f"Job {job_id} not found or session invalid.")
            return
        # 1. Generate Embeddings
        desc_emb = await ai_service.get_embedding(job.description)
        req_emb = await ai_service.get_embedding("\n".join(job.requirements))
        resp_emb = await ai_service.get_embedding("\n".join(job.responsibilities))

        # 2. Assign to Job
        job.description_embedding = desc_emb
        job.requirements_embedding = req_emb
        job.responsibilities_embedding = resp_emb
        
        session.add(job)
