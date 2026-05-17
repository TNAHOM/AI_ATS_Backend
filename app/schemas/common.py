from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.models.job_applicant import ProgressStatus

PayloadT = TypeVar("PayloadT")


class ResponseMeta(BaseModel):
    total: int
    skip: int
    limit: int


class ResponseEnvelope(BaseModel, Generic[PayloadT]):
    model_config = ConfigDict(extra="forbid")

    success: bool = Field(...,
                          description="Indicates if the request succeeded")
    message: str = Field(..., description="Human-readable summary message")
    data: PayloadT | None = Field(default=None, description="Success payload")
    error: str | None = Field(
        default=None, description="Stable application error code")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata")
    # Add this field for pagination metadata
    meta: Optional[ResponseMeta] = None


class PaginatedPayload(BaseModel, Generic[PayloadT]):
    model_config = ConfigDict(extra="forbid")

    items: list[PayloadT] = Field(
        default_factory=list, description="Page items")
    total: int = Field(..., ge=0, description="Total number of matching items")
    page: int = Field(..., ge=1, description="Current page number (1-based)")
    size: int = Field(..., ge=1, description="Number of items per page")
    status_counts: dict[ProgressStatus, int] = Field(
        default_factory=dict, description="Count of applicants for each status"
    )


class MessageData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


class StatusData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
