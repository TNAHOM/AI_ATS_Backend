import enum
import uuid
import datetime
import sqlalchemy as sa

from sqlmodel import Field, SQLModel, Column
from pgvector.sqlalchemy import Vector

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
    description_embedding: list[float] | None = Field(sa_column=Column(Vector(3072)))
    requirements_embedding: list[float] | None = Field(sa_column=Column(Vector(3072)))
    responsibilities_embedding: list[float] | None = Field(sa_column=Column(Vector(3072)))
    
    deadline: datetime.datetime