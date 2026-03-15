from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr

from app.core.database import get_async_session
from app.models.job_applicant import SeniorityStatus
from app.schemas.common import ResponseEnvelope
from app.schemas.job_applicant import (
    JobApplicantCreate,
    JobApplicantResponse,
    JobApplicantVectorSearchData,
)
from app.services.job_applicant_service import job_applicant_service
from app.services.vector_service import vector_search_service
from app.worker.process_job_applicant import process_job_applicant



router = APIRouter(
    prefix="/job-applicants",
    tags=["job-applicants"]
)

@router.post(
    "/",
    response_model=ResponseEnvelope[JobApplicantResponse],
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
    return ResponseEnvelope[JobApplicantResponse](
        success=True,
        message="Job applicant created successfully.",
        data=JobApplicantResponse.model_validate(new_job_applicant),
    )


@router.get(
    "/vector-search/{job_post_id}",
    response_model=ResponseEnvelope[JobApplicantVectorSearchData],
    summary="Rank applicants by vector similarity",
    description="Returns top applicants for a job ranked by weighted cosine similarity.",
)
async def rank_applicants_by_vector_similarity(
    job_post_id: UUID,
    top_k: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    ranked_applicants = await vector_search_service.rank_applicants_for_job(
        db=session,
        job_post_id=job_post_id,
        top_k=top_k,
    )

    return ResponseEnvelope[JobApplicantVectorSearchData](
        success=True,
        message="Applicants ranked successfully.",
        data=JobApplicantVectorSearchData(
            job_post_id=job_post_id,
            total_candidates=len(ranked_applicants),
            ranked_applicants=ranked_applicants,
        ),
    )