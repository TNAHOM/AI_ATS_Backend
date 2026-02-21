from __future__ import annotations

from typing import List, Optional
from uuid import UUID
import datetime

from pydantic import BaseModel
from pydantic import ConfigDict

from app.models.job import LocationType


class JobCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    title: str
    description: str
    location: LocationType
    salary: float
    responsibilities: List[str]
    requirements: List[str]
    deadline: datetime.datetime


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
    description_embedding: Optional[List[float]] = None
    requirements_embedding: Optional[List[float]] = None
    responsibilities_embedding: Optional[List[float]] = None
    deadline: datetime.datetime