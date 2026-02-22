import enum
import uuid
from pgvector.sqlalchemy import Vector
from sqlmodel import Column, Field, SQLModel
import sqlalchemy as sa


class ProgressStatus(str, enum.Enum):
    APPLIED = "APPLIED"
    SHORTLISTED = "SHORTLISTED"
    INTERVIEWING = "INTERVIEWING"
    REJECTED = "REJECTED"
    HIRED = "HIRED"
    
class SeniorityStatus(str, enum.Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    
class ApplicationStatus(str, enum.Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class JobApplicant(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_post_id: uuid.UUID = Field(foreign_key="job.id")
    
    name: str
    email: str
    phone_number: str
    
    original_filename: str
    s3_path: str | None = Field(default=None, unique=True, index=True)
    progress_status: ProgressStatus = Field(default=ProgressStatus.APPLIED)
    seniority_level: SeniorityStatus | None = Field(default=None)
    
    application_status: ApplicationStatus = Field(default=ApplicationStatus.PENDING)
    
    # this is going to contain a json file {'weakness': [], 'strengths': [], 'score': 8.5}
    analysis: dict | None = Field(
        default_factory=lambda: {"weakness": [], "strengths": [], "score": None},
        sa_column=Column(sa.JSON, nullable=True),
    )

    
    failed_reason: str | None = Field(default=None)
    extracted_data: dict | None = Field(default=None, sa_column=Column(sa.JSON, nullable=True))
    embedded_value: list[float] | None = Field(sa_column=Column(Vector(768)), default=None)
