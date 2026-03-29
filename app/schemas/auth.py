from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clerk_id: str = Field(..., description="Clerk subject claim")
    email: str | None = Field(default=None, description="Primary email address")
    internal_user_id: UUID | None = Field(default=None, description="Internal database user id")
    is_active: bool = Field(default=True, description="User active flag")
    is_superuser: bool = Field(default=False, description="Superuser flag")
