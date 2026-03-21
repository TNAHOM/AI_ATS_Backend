from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr

from app.core.database import get_async_session
from app.dependencies import current_active_user
from app.models.job_applicant import ApplicationStatus, ProgressStatus, SeniorityStatus
from app.schemas.common import PaginatedPayload, ResponseEnvelope
from app.schemas.job_applicant import (
    JobApplicantCreate,
    JobApplicantResponse,
    JobApplicantSortField,
    JobApplicantVectorSearchData,
    SortOrder,
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


@router.post(
    "/{applicant_id}/retry",
    response_model=ResponseEnvelope[JobApplicantResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry a failed or dead-letter job applicant",
    description=(
        "Re-triggers background processing for a job applicant whose status is "
        "FAILED or DEAD_LETTER.  The retry counter is reset to zero before the "
        "task is re-queued, giving the applicant a full set of fresh attempts.  "
        "Returns 409 if the applicant is not in a retryable state."
    ),
)
async def retry_job_applicant(
    applicant_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
) -> ResponseEnvelope[JobApplicantResponse]:
    applicant, resume_bytes = await job_applicant_service.get_applicant_for_retry(
        db=session,
        applicant_id=applicant_id,
    )
    background_tasks.add_task(
        process_job_applicant,
        job_applicant_id=applicant.id,
        resume_bytes=resume_bytes,
    )
    return ResponseEnvelope[JobApplicantResponse](
        success=True,
        message="Job applicant processing has been re-queued.",
        data=JobApplicantResponse.model_validate(applicant),
    )


@router.get(
    "/",
    response_model=ResponseEnvelope[PaginatedPayload[JobApplicantResponse]],
    dependencies=[Depends(current_active_user)],
    summary="List job applicants",
    description=(
        "Returns a paginated, filtered, and sorted list of job applicants. "
        "Filter by job posting, progress status, seniority, processing status, and AI score range. "
        "Sort by application date, name, or AI score in ascending or descending order."
    ),
)
async def list_job_applicants(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    job_post_id: UUID | None = Query(default=None, description="Filter by job posting ID"),
    progress_status: ProgressStatus | None = Query(default=None, description="Filter by recruiter progress status"),
    seniority_level: SeniorityStatus | None = Query(default=None, description="Filter by declared seniority level"),
    application_status: ApplicationStatus | None = Query(default=None, description="Filter by processing/application status"),
    min_score: float | None = Query(default=None, ge=0, le=10, description="Minimum AI analysis score (0–10)"),
    max_score: float | None = Query(default=None, ge=0, le=10, description="Maximum AI analysis score (0–10)"),
    sort_by: JobApplicantSortField = Query(default=JobApplicantSortField.APPLIED_AT, description="Field to sort by"),
    sort_order: SortOrder = Query(default=SortOrder.DESC, description="Sort direction"),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseEnvelope[PaginatedPayload[JobApplicantResponse]]:
    applicants, total = await job_applicant_service.list_job_applicants(
        db=session,
        page=page,
        size=size,
        job_post_id=job_post_id,
        progress_status=progress_status,
        seniority_level=seniority_level,
        application_status=application_status,
        min_score=min_score,
        max_score=max_score,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return ResponseEnvelope[PaginatedPayload[JobApplicantResponse]](
        success=True,
        message="Job applicants retrieved successfully.",
        data=PaginatedPayload[JobApplicantResponse](
            items=[JobApplicantResponse.model_validate(a) for a in applicants],
            total=total,
            page=page,
            size=size,
        ),
    )


@router.get(
    "/vector-search/{job_post_id}",
    response_model=ResponseEnvelope[JobApplicantVectorSearchData],
    dependencies=[Depends(current_active_user)],
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


@router.get(
    "/{applicant_id}",
    response_model=ResponseEnvelope[JobApplicantResponse],
    dependencies=[Depends(current_active_user)],
    summary="Get a job applicant by ID",
    description="Returns the full profile of a single job applicant.",
)
async def get_job_applicant(
    applicant_id: UUID,
    session: AsyncSession = Depends(get_async_session),
) -> ResponseEnvelope[JobApplicantResponse]:
    applicant = await job_applicant_service.get_job_applicant(db=session, applicant_id=applicant_id)
    return ResponseEnvelope[JobApplicantResponse](
        success=True,
        message="Job applicant retrieved successfully.",
        data=JobApplicantResponse.model_validate(applicant),
    )
