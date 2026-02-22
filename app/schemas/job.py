from __future__ import annotations

from typing import List, Optional
from uuid import UUID
import datetime

from pydantic import BaseModel, field_validator, Field
from pydantic import ConfigDict

from app.models.job import LocationType


class JobCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # user_id: UUID
    title: str
    description: str
    location: LocationType
    salary: float
    responsibilities: List[str]
    requirements: List[str]
    deadline: datetime.datetime = Field(
        ..., 
        description="Deadline for job application. Must be a naive datetime (no timezone).",
        examples=["2026-02-22T18:40:39"]
    )
    description_embedding: Optional[List[float]] = None
    requirements_embedding: Optional[List[float]] = None
    responsibilities_embedding: Optional[List[float]] = None

    @field_validator("deadline")
    def ensure_naive_datetime(cls, v: datetime.datetime) -> datetime.datetime:
        if v.tzinfo is not None:
            # Remove timezone info to make it naive
            return v.replace(tzinfo=None)
        return v


class JobUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: Optional[UUID]
    title: Optional[str]
    description: Optional[str]
    location: Optional[LocationType]
    salary: Optional[float]
    responsibilities: Optional[List[str]]
    requirements: Optional[List[str]]
    deadline: Optional[datetime.datetime]

class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    description: str
    applicant_count: int
    location: LocationType
    salary: float
    responsibilities: List[str]
    requirements: List[str]
    deadline: datetime.datetime