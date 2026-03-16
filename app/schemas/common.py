from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

PayloadT = TypeVar("PayloadT")


class ResponseEnvelope(BaseModel, Generic[PayloadT]):
    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="Indicates if the request succeeded")
    message: str = Field(..., description="Human-readable summary message")
    data: PayloadT | None = Field(default=None, description="Success payload")
    error: str | None = Field(default=None, description="Stable application error code")
    details: dict[str, Any] = Field(default_factory=dict, description="Optional metadata")


class PaginatedPayload(BaseModel, Generic[PayloadT]):
    model_config = ConfigDict(extra="forbid")

    items: list[PayloadT] = Field(default_factory=list, description="Page items")
    total: int = Field(..., ge=0, description="Total number of matching items")
    page: int = Field(..., ge=1, description="Current page number (1-based)")
    size: int = Field(..., ge=1, description="Number of items per page")


class MessageData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


class StatusData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
