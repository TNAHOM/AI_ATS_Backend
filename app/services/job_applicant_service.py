import logging

from fastapi import status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions import BaseAppException, S3ServiceError
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

        # Pre-check: reject duplicate application before touching S3, so we
        # avoid orphaning an upload and get a clean 409 without any DB error.
        existing_result = await db.execute(
            select(JobApplicant).where(
                JobApplicant.job_post_id == job_applicant_data.job_post_id,
                JobApplicant.email == job_applicant_data.email.lower(),
            )
        )
        if existing_result.scalar_one_or_none() is not None:
            raise BaseAppException(
                error_code="DUPLICATE_APPLICATION",
                message="An application for this job with the same email already exists.",
                status_code=status.HTTP_409_CONFLICT,
            )

        s3_path: str | None = None
        try:
            s3_path = await s3_service.upload_document(
                file_bytes=resume_bytes,
                original_filename=resume_filename,
                content_type="application/pdf",
            )

            job_applicant = JobApplicant(
                **job_applicant_data.model_dump(),
                s3_path=s3_path,
                original_filename=resume_filename,
                application_status=ApplicationStatus.QUEUED,
            )

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
        except IntegrityError as e:
            try:
                await db.rollback()
            except SQLAlchemyError as rollback_error:
                logger.warning("Rollback failed after IntegrityError: %s", type(rollback_error).__name__)
            # Best-effort cleanup of uploaded resume on DB integrity errors
            if s3_path:
                try:
                    await s3_service.delete_document(s3_path)
                except S3ServiceError as cleanup_error:
                    logger.warning(
                        "Failed to delete orphaned resume from S3 after IntegrityError: %s",
                        cleanup_error,
                    )
            # str(e) (SQLAlchemy exception) always contains the full error text
            # including the constraint name, unlike str(e.orig) which may be
            # empty when using the asyncpg driver.
            constraint = getattr(getattr(e.orig, "diag", None), "constraint_name", None)
            error_text = constraint if constraint else str(e)
            if "uq_job_applicant_job_post_email" in error_text:
                logger.warning(
                    "Duplicate application attempt for job_post_id=%s email=%s",
                    job_applicant_data.job_post_id,
                    job_applicant_data.email,
                )
                raise BaseAppException(
                    error_code="DUPLICATE_APPLICATION",
                    message="An application for this job with the same email already exists.",
                    status_code=status.HTTP_409_CONFLICT,
                )
            logger.error("Integrity constraint violation while creating job applicant: %s", type(e).__name__)
            raise BaseAppException(
                error_code="JOB_APPLICANT_CREATE_FAILED",
                message="Failed to create job applicant due to a data constraint violation.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except SQLAlchemyError as e:
            try:
                await db.rollback()
            except SQLAlchemyError as rollback_error:
                logger.warning("Rollback failed after SQLAlchemyError: %s", type(rollback_error).__name__)
            # Best-effort cleanup of uploaded resume on general DB errors
            if s3_path:
                try:
                    await s3_service.delete_document(s3_path)
                except S3ServiceError as cleanup_error:
                    logger.warning(
                        "Failed to delete orphaned resume from S3 after SQLAlchemyError: %s",
                        cleanup_error,
                    )
            logger.error("Database error while creating job applicant: %s: %s", type(e).__name__, str(e))
            raise BaseAppException(
                error_code="JOB_APPLICANT_CREATE_FAILED",
                message="Failed to create job applicant.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


job_applicant_service = JobApplicantService()
