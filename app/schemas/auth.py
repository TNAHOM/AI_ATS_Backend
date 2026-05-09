from typing import Any, Dict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VerifiedClerkToken(BaseModel):
    clerk_id: str
    email: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clerk_id: str = Field(..., description="Clerk subject claim")
    email: str = Field(..., description="Primary email address")
    internal_user_id: UUID = Field(...,
                                   description="Internal database user id")
    is_active: bool = Field(default=True, description="User active flag")
    is_superuser: bool = Field(default=False, description="Superuser flag")


class ProvisionRequest(BaseModel):
    first_name: str
    last_name: str
    phone_number: str = ""
