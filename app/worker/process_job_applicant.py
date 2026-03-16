import asyncio
import logging
import math
import uuid
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from app.core.exceptions import AIServiceError
from app.models.job import Job
from app.models.job_applicant import ApplicationStatus, JobApplicant
from app.services.ai_service import ai_service
from app.worker.utils import task_monitor

logger = logging.getLogger(__name__)


def _safe_cosine_similarity(vector_a: list[float] | None, vector_b: list[float] | None) -> float:
    if vector_a is None or vector_b is None:
        return 0.0

    if len(vector_a) != len(vector_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    similarity = dot / (norm_a * norm_b)
    return max(0.0, min(1.0, similarity))


def _to_json_compatible(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _to_json_compatible(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_to_json_compatible(item) for item in value]

    if isinstance(value, tuple):
        return [_to_json_compatible(item) for item in value]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    item_method = getattr(value, "item", None)
    if callable(item_method):
        try:
            return item_method()
        except (TypeError, ValueError, OverflowError):
            return str(value)

    return str(value)


async def process_job_applicant(job_applicant_id: uuid.UUID, resume_bytes: bytes) -> None:
    """
    Background task to process a job applicant after creation.
    This task currently transitions applicant processing states and is ready for
    extraction, grading, and embedding steps.
    """
    logger.info("Starting background processing for Job Applicant %s", job_applicant_id)

    async with task_monitor(JobApplicant, job_applicant_id) as (job_applicant, session):
        job_applicant: JobApplicant | None
        if not job_applicant or not session:
            logger.warning("Job Applicant %s not found or session invalid.", job_applicant_id)
            return

        try:
            job_applicant.application_status = ApplicationStatus.PROCESSING
            session.add(job_applicant)
            await session.commit()
            await session.refresh(job_applicant)

            job_result = await session.execute(
                select(Job).where(Job.id == job_applicant.job_post_id)
            )
            job = job_result.scalar_one_or_none()
            if not job:
                raise ValueError("Job post not found for applicant analysis.")

            extracted_resume = await ai_service.extract_resume_info(resume_bytes)
            normalized_resume_json = extracted_resume.model_dump_json()

            resume_embedding, ai_analysis = await asyncio.gather(
                ai_service.get_embedding(normalized_resume_json),
                ai_service.analyze_resume_against_job_post(
                    normalized_resume_json=normalized_resume_json,
                    job_description=job.description,
                    job_requirements=job.requirements,
                    job_responsibilities=job.responsibilities,
                ),
            )

            description_embedding = job.description_embedding
            requirements_embedding = job.requirements_embedding
            responsibilities_embedding = job.responsibilities_embedding

            if description_embedding is None:
                description_embedding = await ai_service.get_embedding(job.description)

            if requirements_embedding is None:
                requirements_embedding = await ai_service.get_embedding("\n".join(job.requirements))

            if responsibilities_embedding is None:
                responsibilities_embedding = await ai_service.get_embedding("\n".join(job.responsibilities))

            desc_similarity = _safe_cosine_similarity(resume_embedding, description_embedding)
            req_similarity = _safe_cosine_similarity(resume_embedding, requirements_embedding)
            resp_similarity = _safe_cosine_similarity(resume_embedding, responsibilities_embedding)

            ai_score_normalized = max(0.0, min(1.0, ai_analysis.score / 100.0))
            penalty_points = min(len(ai_analysis.weaknesses) * 2, 10.0)

            weighted_score_100 = (
                (req_similarity * 40.0)
                + (resp_similarity * 30.0)
                + (desc_similarity * 20.0)
                + (ai_score_normalized * 10.0)
                - penalty_points
            )
            weighted_score_100 = max(0.0, min(100.0, weighted_score_100))

            final_score_10 = float(round(weighted_score_100 / 10.0, 2))

            extracted_data_payload: dict[str, Any] = _to_json_compatible(extracted_resume.model_dump())
            analysis_payload: dict[str, Any] = _to_json_compatible(
                {
                    "score": final_score_10,
                    "strengths": ai_analysis.strengths,
                    "weakness": ai_analysis.weaknesses,
                }
            )
            embedding_payload = [float(v) for v in resume_embedding]

            job_applicant.extracted_data = extracted_data_payload
            job_applicant.embedded_value = embedding_payload
            job_applicant.analysis = {
                "score": analysis_payload["score"],
                "strengths": analysis_payload["strengths"],
                "weakness": analysis_payload["weakness"],
            }
            job_applicant.application_status = ApplicationStatus.COMPLETED
            session.add(job_applicant)
            await session.commit()

        except (SQLAlchemyError, AIServiceError, ValueError, TypeError, AttributeError, RuntimeError):
            await session.rollback()
            job_applicant.application_status = ApplicationStatus.FAILED
            session.add(job_applicant)
            await session.commit()
            raise
