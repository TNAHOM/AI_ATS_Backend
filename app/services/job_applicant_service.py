import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import S3ServiceError
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded resume is empty.",
            )

        normalized_name = resume_filename.lower()
        is_pdf_name = normalized_name.endswith(".pdf")
        is_pdf_type = resume_content_type in {"application/pdf", "application/x-pdf"}
        if not is_pdf_name and not is_pdf_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resume must be a PDF file.",
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
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to upload resume to storage.",
            )
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error("Database error while creating job applicant: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create job applicant.",
            )


job_applicant_service = JobApplicantService()
