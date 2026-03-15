from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr

from app.core.database import get_async_session
from app.models.job_applicant import SeniorityStatus
from app.schemas.job_applicant import JobApplicantCreate, JobApplicantResponse
from app.services.job_applicant_service import job_applicant_service
from app.worker.process_job_applicant import process_job_applicant



router = APIRouter(
    prefix="/job-applicants",
    tags=["job-applicants"]
)

@router.post(
    "/",
    response_model=JobApplicantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job applicant",
    description="Create a new job applicant by uploading a resume PDF with applicant information.",
)
async def create_job_applicant(
    background_tasks: BackgroundTasks,
    job_post_id: UUID = Form(...),
    name: str = Form(...),
    email: EmailStr = Form(...),
    phone_number: str = Form(...),
    seniority_level: SeniorityStatus | None = Form(default=None),
    resume: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
):
    job_applicant_in = JobApplicantCreate(
        job_post_id=job_post_id,
        name=name,
        email=email,
        phone_number=phone_number,
        seniority_level=seniority_level,
    )

    resume_bytes = await resume.read()

    new_job_applicant = await job_applicant_service.create_job_applicant(
        db=session,
        job_applicant_data=job_applicant_in,
        resume_bytes=resume_bytes,
        resume_filename=resume.filename or "resume.pdf",
        resume_content_type=resume.content_type,
    )

    background_tasks.add_task(process_job_applicant, job_applicant_id=new_job_applicant.id, resume_bytes=resume_bytes)
    return JobApplicantResponse.model_validate(new_job_applicant)