import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr

from app.core.database import get_async_session
from app.dependencies import current_active_user
from app.models.job_applicant import ApplicationStatus, ProgressStatus, SeniorityStatus
from app.schemas.common import PaginatedPayload, ResponseEnvelope, ResponseMeta
from app.schemas.job_applicant import (
    JobApplicantCreate,
    JobApplicantResponse,
    JobApplicantSortField,
    JobApplicantVectorSearchData,
    ResumeUrlData,
    SortOrder,
)
from app.services.job_applicant_service import job_applicant_service
from app.services.vector_service import vector_search_service
from app.worker.process_job_applicant import process_job_applicant
from app.services.aws_service import s3_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/job-applicants",
    tags=["job-applicants"]
)


@router.post(
    "",
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
    logger.info(f"Creating job applicant {email} for job {job_post_id}")
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

    background_tasks.add_task(
        process_job_applicant, job_applicant_id=new_job_applicant.id, resume_bytes=resume_bytes)
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
    logger.info(
        f"Retrying application processing for applicant {applicant_id}")
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
    "",
    response_model=ResponseEnvelope[PaginatedPayload[JobApplicantResponse]],
    dependencies=[Depends(current_active_user)],
    summary="List job applicants",
    description=(
        "Returns a paginated, filtered, and sorted list of job applicants. "
        "Filter by job posting, progress status, seniority, application status, and AI score range. "
        "Sort by application date, name, or AI score in ascending or descending order."
    ),
)
async def list_job_applicants(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    size: int = Query(default=20, ge=1, le=100,
                      description="Number of items per page"),
    job_post_id: UUID | None = Query(
        default=None, description="Filter by job posting ID"),
    progress_status: ProgressStatus | None = Query(
        default=None, description="Filter by recruiter progress status"),
    seniority_level: SeniorityStatus | None = Query(
        default=None, description="Filter by declared seniority level"),
    application_status: ApplicationStatus | None = Query(
        default=None, description="Filter by processing/application status"),
    min_score: float | None = Query(
        default=None, ge=0, le=10, description="Minimum AI analysis score (0–10)"),
    max_score: float | None = Query(
        default=None, ge=0, le=10, description="Maximum AI analysis score (0–10)"),
    sort_by: JobApplicantSortField = Query(
        default=JobApplicantSortField.APPLIED_AT, description="Field to sort by"),
    sort_order: SortOrder = Query(
        default=SortOrder.DESC, description="Sort direction"),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseEnvelope[PaginatedPayload[JobApplicantResponse]]:
    logger.info(
        f"Listing job applicants (page={page}, size={size}, job_post_id={job_post_id})")
    applicants, total, status_counts = await job_applicant_service.list_job_applicants(
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
            size=size,
            page=page,
            status_counts=status_counts,
        ),
        meta=ResponseMeta(
            total=total,
            skip=(page - 1) * size,
            limit=size,
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
    logger.info(
        f"Ranking applicants for job {job_post_id} with vector similarity (top_k={top_k})")
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
    logger.info(f"Fetching job applicant {applicant_id}")
    applicant = await job_applicant_service.get_job_applicant(db=session, applicant_id=applicant_id)
    return ResponseEnvelope[JobApplicantResponse](
        success=True,
        message="Job applicant retrieved successfully.",
        data=JobApplicantResponse.model_validate(applicant),
    )


@router.patch(
    "/advance-applicant/{next_status_name}",
    response_model=ResponseEnvelope[JobApplicantResponse],
    dependencies=[Depends(current_active_user)],
    summary="Advance applicant to next progress stage",
    description=(
        "Advances an applicant to the next allowed recruiter progress stage. "
        "Provide applicant_id as a query parameter and the desired next status in the path."
    ),
)
async def advance_job_applicant_status(
    next_status_name: str,
    applicant_id: UUID = Query(..., description="Applicant ID to advance"),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseEnvelope[JobApplicantResponse]:
    logger.info(
        f"Advancing applicant {applicant_id} to status {next_status_name}")
    applicant = await job_applicant_service.advance_applicant_progress_status(
        db=session,
        applicant_id=applicant_id,
        next_status_name=next_status_name,
    )

    return ResponseEnvelope[JobApplicantResponse](
        success=True,
        message="Applicant progress status advanced successfully.",
        data=JobApplicantResponse.model_validate(applicant),
    )


@router.get(
    "/{applicant_id}/resume-url",
    response_model=ResponseEnvelope[ResumeUrlData],
    dependencies=[Depends(current_active_user)],
    summary="Get a secure viewing URL for the applicant's resume",
    description="Generates a 15-minute pre-signed S3 URL to securely view the applicant's PDF resume in the browser.",
)
async def get_applicant_resume_url(
    applicant_id: UUID,
    session: AsyncSession = Depends(get_async_session),
) -> ResponseEnvelope[ResumeUrlData]:
    logger.info(
        f"Generating resume pre-signed URL for applicant {applicant_id}")

    # 1. Fetch applicant using existing service
    applicant = await job_applicant_service.get_job_applicant(db=session, applicant_id=applicant_id)

    # 2. Safety check: ensure the applicant has an S3 path
    if not applicant.s3_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume file not found for this applicant."
        )

    # 3. Use your S3 Service to generate the URL (Exceptions handled inside the service)
    presigned_url = await s3_service.generate_presigned_url(
        s3_key=applicant.s3_path,
        original_filename=applicant.original_filename or "resume.pdf"
    )

    # 4. Return standard response
    return ResponseEnvelope[ResumeUrlData](
        success=True,
        message="Resume secure link generated successfully.",
        data=ResumeUrlData(url=presigned_url)
    )
