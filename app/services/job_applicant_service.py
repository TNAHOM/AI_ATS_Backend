import logging
from typing import Sequence
from uuid import UUID

from fastapi import status
from sqlalchemy import Float, asc, case, cast, desc, func, nullslast, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BaseAppException, S3ServiceError
from app.models.job_applicant import ApplicationStatus, JobApplicant, ProgressStatus, SeniorityStatus
from app.schemas.job_applicant import JobApplicantCreate, JobApplicantSortField, SortOrder
from app.services.aws_service import s3_service

logger = logging.getLogger(__name__)


class JobApplicantService:
    async def create_job_applicant(
        self,
        db: AsyncSession,
        job_applicant_data: JobApplicantCreate,
        resume_bytes: bytes,
        resume_filename: str,
        resume_content_type: str | None,
    ) -> JobApplicant:
        if not resume_bytes:
            raise BaseAppException(
                error_code="EMPTY_RESUME",
                message="Uploaded resume is empty.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        normalized_name = resume_filename.lower()
        is_pdf_name = normalized_name.endswith(".pdf")
        is_pdf_type = resume_content_type in {"application/pdf", "application/x-pdf"}
        if not is_pdf_name and not is_pdf_type:
            raise BaseAppException(
                error_code="INVALID_RESUME_FORMAT",
                message="Resume must be a PDF file.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            s3_path = await s3_service.upload_document(
                file_bytes=resume_bytes,
                original_filename=resume_filename,
                content_type="application/pdf",
            )

            job_applicant = JobApplicant(**job_applicant_data.model_dump(), s3_path=s3_path, original_filename=resume_filename, application_status=ApplicationStatus.QUEUED)

            db.add(job_applicant)
            await db.commit()
            await db.refresh(job_applicant)

            logger.info("Successfully created job applicant with ID: %s", job_applicant.id)
            return job_applicant

        except S3ServiceError as e:
            logger.error("S3 upload error while creating job applicant: %s", e)
            raise BaseAppException(
                error_code="RESUME_UPLOAD_FAILED",
                message="Failed to upload resume to storage.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error("Database error while creating job applicant: %s", e)
            raise BaseAppException(
                error_code="JOB_APPLICANT_CREATE_FAILED",
                message="Failed to create job applicant.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    async def get_job_applicant(self, db: AsyncSession, applicant_id: UUID) -> JobApplicant:
        """Fetch a single job applicant by ID."""
        try:
            result = await db.execute(select(JobApplicant).where(JobApplicant.id == applicant_id))
            applicant = result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error("Database error while fetching applicant %s: %s", applicant_id, e)
            raise BaseAppException(
                error_code="JOB_APPLICANT_FETCH_FAILED",
                message="Failed to retrieve job applicant.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if applicant is None:
            raise BaseAppException(
                error_code="JOB_APPLICANT_NOT_FOUND",
                message="Job applicant not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return applicant

    async def list_job_applicants(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        job_post_id: UUID | None = None,
        progress_status: ProgressStatus | None = None,
        seniority_level: SeniorityStatus | None = None,
        application_status: ApplicationStatus | None = None,
        min_score: float | None = None,
        max_score: float | None = None,
        sort_by: JobApplicantSortField = JobApplicantSortField.APPLIED_AT,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> tuple[Sequence[JobApplicant], int]:
        """
        Return a paginated, filtered, and sorted list of job applicants.

        Filters: job_post_id, progress_status, seniority_level, application_status,
                 min_score / max_score (based on AI analysis.score, 0-10 scale).
        Sorting: applied_at | name | score  ×  asc | desc  (nulls always last).
        Pagination: 1-based page + size.
        """
        # Cast analysis.score to Float safely; yields NULL when analysis is NULL
        # or when the key is absent, which integrates correctly with nullslast().
        score_col = case(
            (JobApplicant.analysis.isnot(None), cast(JobApplicant.analysis["score"].astext, Float)),
            else_=None,
        )

        conditions = []
        if job_post_id is not None:
            conditions.append(JobApplicant.job_post_id == job_post_id)
        if progress_status is not None:
            conditions.append(JobApplicant.progress_status == progress_status)
        if seniority_level is not None:
            conditions.append(JobApplicant.seniority_level == seniority_level)
        if application_status is not None:
            conditions.append(JobApplicant.application_status == application_status)
        if min_score is not None:
            conditions.append(score_col >= min_score)
        if max_score is not None:
            conditions.append(score_col <= max_score)

        # Explicit mapping ensures new enum values surface as KeyError instead
        # of silently falling back to a wrong default.
        sort_col_map = {
            JobApplicantSortField.APPLIED_AT: JobApplicant.applied_at,
            JobApplicantSortField.NAME: JobApplicant.name,
            JobApplicantSortField.SCORE: score_col,
        }
        raw_sort_col = sort_col_map[sort_by]

        order_expr = nullslast(desc(raw_sort_col)) if sort_order == SortOrder.DESC else nullslast(asc(raw_sort_col))

        list_query = select(JobApplicant)
        count_query = select(func.count()).select_from(JobApplicant)
        if conditions:
            list_query = list_query.where(*conditions)
            count_query = count_query.where(*conditions)

        offset = (page - 1) * size
        list_query = list_query.order_by(order_expr).offset(offset).limit(size)

        try:
            result = await db.execute(list_query)
            applicants = result.scalars().all()

            count_result = await db.execute(count_query)
            total = int(count_result.scalar_one())
        except SQLAlchemyError as e:
            logger.error("Database error while listing applicants: %s", e)
            raise BaseAppException(
                error_code="JOB_APPLICANT_LIST_FAILED",
                message="Failed to retrieve job applicants.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return applicants, total


job_applicant_service = JobApplicantService()
