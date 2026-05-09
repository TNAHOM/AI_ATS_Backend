from pydantic import BaseModel
from typing import Literal
from app.schemas.Clerk.clerk_user import ClerkUserData

class ClerkWebhookEvent(BaseModel):
    model_config = {
        "extra": "ignore"
    }
    object: Literal["event"]

    type: Literal[
        "user.created",
        "user.updated",
        "user.deleted"
    ]

    timestamp: int

    instance_id: str

    data: ClerkUserData