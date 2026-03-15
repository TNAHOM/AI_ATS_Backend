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


class MessageData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


class StatusData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
