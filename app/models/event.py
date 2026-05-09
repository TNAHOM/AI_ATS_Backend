from sqlmodel import SQLModel, Field
from datetime import datetime, timezone


class ProcessedWebhookEvent(SQLModel, table=True):
    svix_id: str = Field(primary_key=True)
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )