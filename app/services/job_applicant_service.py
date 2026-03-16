import logging
import uuid

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions import BaseAppException, S3ServiceError
from app.models.common import ProcessingStatus
from app.models.job_applicant import ApplicationStatus, JobApplicant
from app.schemas.job_applicant import JobApplicantCreate
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

    async def get_applicant_for_retry(
        self,
        db: AsyncSession,
        applicant_id: uuid.UUID,
    ) -> tuple[JobApplicant, bytes]:
        """
        Fetch a job applicant that is in FAILED or DEAD_LETTER state and
        download its resume bytes from S3 so the caller can re-trigger processing.

        Raises ``BaseAppException`` with appropriate error codes on failure.
        """
        try:
            result = await db.execute(
                select(JobApplicant).where(JobApplicant.id == applicant_id)
            )
            job_applicant = result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error("Database error fetching applicant %s for retry: %s", applicant_id, e)
            raise BaseAppException(
                error_code="APPLICANT_FETCH_FAILED",
                message="Failed to retrieve job applicant.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not job_applicant:
            raise BaseAppException(
                error_code="APPLICANT_NOT_FOUND",
                message="Job applicant not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        retryable_statuses = {ApplicationStatus.FAILED, ApplicationStatus.DEAD_LETTER}
        if job_applicant.application_status not in retryable_statuses:
            raise BaseAppException(
                error_code="APPLICANT_NOT_RETRYABLE",
                message=(
                    f"Job applicant cannot be retried in its current state: "
                    f"{job_applicant.application_status.value}."
                ),
                status_code=status.HTTP_409_CONFLICT,
                details={"current_status": job_applicant.application_status.value},
            )

        if job_applicant.processing_status == ProcessingStatus.PROCESSING:
            raise BaseAppException(
                error_code="APPLICANT_ALREADY_PROCESSING",
                message="Job applicant is currently being processed; retry is not allowed until processing completes.",
                status_code=status.HTTP_409_CONFLICT,
                details={"processing_status": job_applicant.processing_status.value},
            )

        if not job_applicant.s3_path:
            raise BaseAppException(
                error_code="RESUME_NOT_FOUND",
                message="No resume on record for this applicant; cannot retry.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        try:
            resume_bytes = await s3_service.download_document(job_applicant.s3_path)
        except S3ServiceError as e:
            logger.error(
                "S3 download failed for applicant %s (key: %s): %s",
                applicant_id,
                job_applicant.s3_path,
                e,
            )
            raise BaseAppException(
                error_code="RESUME_DOWNLOAD_FAILED",
                message="Failed to download resume from storage.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        # Reset retry counter and status so the worker starts fresh.
        try:
            job_applicant.retry_count = 0
            job_applicant.application_status = ApplicationStatus.QUEUED
            job_applicant.failed_reason = None
            db.add(job_applicant)
            await db.commit()
            await db.refresh(job_applicant)
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error("Database error resetting applicant %s for retry: %s", applicant_id, e)
            raise BaseAppException(
                error_code="APPLICANT_RETRY_RESET_FAILED",
                message="Failed to reset applicant state for retry.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "Applicant %s reset to QUEUED for retry (retry_count=0).",
            applicant_id,
        )
        return job_applicant, resume_bytes


job_applicant_service = JobApplicantService()
