from __future__ import annotations

from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.job_applicant import (
    ProgressStatus, 
    SeniorityStatus, 
    ApplicationStatus
)

class ApplicantAnalysis(BaseModel):
    weakness: List[str] = []
    strengths: List[str] = []
    score: Optional[float] = None


class JobApplicantCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)

    job_post_id: UUID
    name: str
    email: EmailStr
    phone_number: str
    seniority_level: Optional[SeniorityStatus] = None



#TODO: NEED to fx this issue when i implement the update endpoint for job applicant.
class JobApplicantUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    
    # Status Updates
    progress_status: Optional[ProgressStatus] = None
    seniority_level: Optional[SeniorityStatus] = None
    application_status: Optional[ApplicationStatus] = None
    
    s3_path: Optional[str] = None
    analysis: Optional[ApplicantAnalysis] = None
    failed_reason: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    embedded_value: Optional[List[float]] = None

class JobApplicantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_post_id: UUID
    
    name: str
    email: EmailStr
    phone_number: str
    original_filename: Optional[str] = None
    s3_path: Optional[str] = None
    
    progress_status: ProgressStatus
    seniority_level: Optional[SeniorityStatus] = None
    application_status: ApplicationStatus
    
    analysis: Optional[ApplicantAnalysis] = None
    failed_reason: Optional[str] = None


class JobApplicantVectorResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    applicant: JobApplicantResponse
    similarity_score: float


class JobApplicantVectorSearchData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_post_id: UUID
    total_candidates: int
    ranked_applicants: List[JobApplicantVectorResult]