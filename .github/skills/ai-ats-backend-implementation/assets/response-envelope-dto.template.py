"""
AI Template Only (do not import directly in runtime code).
Copy and adapt into app/schemas/* when implementing endpoint DTOs.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

PayloadT = TypeVar("PayloadT")


class ResponseEnvelope(BaseModel, Generic[PayloadT]):
    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="True for successful responses, false otherwise")
    message: str = Field(..., description="Human-readable summary of the response")
    data: PayloadT | None = Field(default=None, description="Response payload for success cases")
    error: str | None = Field(default=None, description="Stable application error code")
    details: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        description="Optional structured metadata for debugging/client handling",
    )


class PaginatedPayload(BaseModel, Generic[PayloadT]):
    model_config = ConfigDict(extra="forbid")

    items: list[PayloadT] = Field(default_factory=list, description="Page items")
    total: int = Field(..., ge=0, description="Total available items")
    page: int = Field(..., ge=1, description="Current page number")
    size: int = Field(..., ge=1, description="Page size")


# Usage pattern (example)
# class CandidateResponse(BaseModel):
#     id: str
#     full_name: str
#
# CandidateEnvelope = ResponseEnvelope[CandidateResponse]
# CandidateListEnvelope = ResponseEnvelope[PaginatedPayload[CandidateResponse]]
