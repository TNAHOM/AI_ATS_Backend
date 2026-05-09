from pydantic import BaseModel, Field
from typing import Optional, Literal
from typing import Any


class ClerkVerification(BaseModel):
    status: Optional[str] = None
    strategy: Optional[str] = None


class ClerkEmailAddress(BaseModel):
    id: str
    object: Literal["email_address"]

    email_address: str

    verification: Optional[ClerkVerification] = None


class ClerkPhoneNumber(BaseModel):
    id: str
    object: Literal["phone_number"]

    phone_number: str


class ClerkUserData(BaseModel):
    id: str
    # Make optional because deleted event omits this
    object: Optional[str] = None
    deleted: Optional[bool] = False  # For the deleted event

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    image_url: Optional[str] = None
    username: Optional[str] = None

    primary_email_address_id: Optional[str] = None
    primary_phone_number_id: Optional[str] = None

    email_addresses: list[ClerkEmailAddress] = Field(default_factory=list)
    phone_numbers: list[ClerkPhoneNumber] = Field(default_factory=list)

    public_metadata: dict[str, Any] = Field(default_factory=dict)
    private_metadata: dict[str, Any] = Field(default_factory=dict)

    created_at: Optional[int] = None
    updated_at: Optional[int] = None

    last_sign_in_at: Optional[int] = None

    password_enabled: Optional[bool] = None
    two_factor_enabled: Optional[bool] = None
