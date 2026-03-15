import logging
import math
from uuid import UUID

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions import BaseAppException
from app.models.job import Job
from app.models.job_applicant import ApplicationStatus, JobApplicant
from app.schemas.job_applicant import JobApplicantResponse, JobApplicantVectorResult

logger = logging.getLogger(__name__)


def _safe_cosine_similarity(vector_a: list[float] | None, vector_b: list[float] | None) -> float:
    if vector_a is None or vector_b is None:
        return 0.0

    if len(vector_a) != len(vector_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    similarity = dot_product / (norm_a * norm_b)
    return max(0.0, min(1.0, similarity))


class VectorSearchService:
    async def rank_applicants_for_job(
        self,
        db: AsyncSession,
        job_post_id: UUID,
        top_k: int,
    ) -> list[JobApplicantVectorResult]:
        if top_k < 1:
            raise BaseAppException(
                error_code="INVALID_TOP_K",
                message="top_k must be at least 1.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            job_result = await db.execute(select(Job).where(Job.id == job_post_id))
            job = job_result.scalar_one_or_none()
            if not job:
                raise BaseAppException(
                    error_code="JOB_NOT_FOUND",
                    message="Job not found.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            logger.info("Ranking applicants for job: %s", job)
            if (
                job.description_embedding is None
                or job.requirements_embedding is None
                or job.responsibilities_embedding is None
            ):
                raise BaseAppException(
                    error_code="JOB_EMBEDDINGS_NOT_READY",
                    message="Job embeddings are not ready yet.",
                    status_code=status.HTTP_409_CONFLICT,
                )

            applicants_result = await db.execute(
                select(JobApplicant).where(
                    JobApplicant.job_post_id == job_post_id,
                    JobApplicant.application_status == ApplicationStatus.COMPLETED,
                )
            )
            applicants = applicants_result.scalars().all()

            ranked_results: list[JobApplicantVectorResult] = []
            for applicant in applicants:
                if applicant.embedded_value is None:
                    continue

                description_similarity = _safe_cosine_similarity(
                    applicant.embedded_value,
                    job.description_embedding,
                )
                responsibilities_similarity = _safe_cosine_similarity(
                    applicant.embedded_value,
                    job.responsibilities_embedding,
                )
                requirements_similarity = _safe_cosine_similarity(
                    applicant.embedded_value,
                    job.requirements_embedding,
                )

                weighted_similarity = (
                    (description_similarity * 0.20)
                    + (responsibilities_similarity * 0.30)
                    + (requirements_similarity * 0.50)
                )

                ranked_results.append(
                    JobApplicantVectorResult(
                        applicant=JobApplicantResponse.model_validate(applicant),
                        similarity_score=round(weighted_similarity, 4),
                    )
                )

            ranked_results.sort(key=lambda item: item.similarity_score, reverse=True)
            return ranked_results[:top_k]

        except BaseAppException:
            raise
        except SQLAlchemyError as error:
            logger.error("Database error during applicant vector search: %s", error)
            raise BaseAppException(
                error_code="VECTOR_SEARCH_FAILED",
                message="Failed to rank applicants for the job.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


vector_search_service = VectorSearchService()
