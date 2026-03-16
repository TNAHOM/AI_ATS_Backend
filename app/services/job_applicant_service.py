import logging

from fastapi import status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

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
        except IntegrityError as e:
            await db.rollback()
            constraint_name = getattr(getattr(e.orig, "diag", None), "constraint_name", None) or str(e.orig)
            if "uq_job_applicant_job_post_email" in constraint_name:
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
            await db.rollback()
            logger.error("Database error while creating job applicant: %s", e)
            raise BaseAppException(
                error_code="JOB_APPLICANT_CREATE_FAILED",
                message="Failed to create job applicant.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


job_applicant_service = JobApplicantService()
