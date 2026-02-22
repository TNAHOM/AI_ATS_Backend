import enum
import uuid
import datetime
import sqlalchemy as sa

from sqlmodel import Field, SQLModel, Column
from pgvector.sqlalchemy import Vector

from app.models.common import ProcessingStatus

class LocationType(str, enum.Enum):
    REMOTE = "remote"
    ONSITE = "onsite"
    HYBRID = "hybrid"
    
class Job(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    
    title: str
    description: str
    applicant_count: int = Field(default=0)
    
    location: LocationType
    salary: float
    
    responsibilities: list[str] = Field(default_factory=list, sa_column=Column(sa.JSON, nullable=False))
    requirements: list[str] = Field(default_factory=list, sa_column=Column(sa.JSON, nullable=False))
    
    # TODO: remove the None in the future this will be required
    description_embedding: list[float] | None = Field(sa_column=Column(Vector(768)))
    requirements_embedding: list[float] | None = Field(sa_column=Column(Vector(768)))
    responsibilities_embedding: list[float] | None = Field(sa_column=Column(Vector(768)))
    
    deadline: datetime.datetime
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now, sa_column=Column(sa.DateTime, onupdate=datetime.datetime.now))
    
    # For logging and debugging
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    processing_error: str | None = Field(default=None)