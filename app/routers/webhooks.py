# app/routers/webhook.py
import os
import logging
from fastapi import Request, HTTPException, APIRouter, Depends
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from sqlmodel import col
from svix.webhooks import Webhook, WebhookVerificationError

from app.core.database import get_async_session
from app.models.event import ProcessedWebhookEvent
from app.models.user import User, UserType
from app.schemas.Clerk.clerk_event import ClerkWebhookEvent
from app.services.users import upsert_user

logger = logging.getLogger(__name__)

webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@webhook_router.post("/clerk")
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_async_session)):
    logger.info("Received Clerk webhook request")
    secret = os.getenv("CLERK_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(
            status_code=500, detail="Webhook secret not configured")

    payload = await request.body()
    headers = request.headers

    # 1. Validate Svix signature
    try:
        wh = Webhook(secret)
        event = wh.verify(payload, {
            "svix-id": headers.get("svix-id", ""),
            "svix-signature": headers.get("svix-signature", ""),
            "svix-timestamp": headers.get("svix-timestamp", ""),
        })
    except WebhookVerificationError as e:
        logger.error(f"Signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 2. Get the Unique Svix ID
    svix_id = headers.get("svix-id")
    if not svix_id:
        raise HTTPException(status_code=400, detail="Missing svix-id header")

    # 3. IDEMPOTENCY / RETRY SAFETY CHECK
    db.add(ProcessedWebhookEvent(svix_id=svix_id))
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return {"success": True, "message": "Webhook already processed"}

    # 4. PROCESS THE WEBHOOK
    try:
        validated_event = ClerkWebhookEvent.model_validate(event)
        data = validated_event.data
        clerk_user_id = data.id

        # -- Handle Deletion --
        if validated_event.type == "user.deleted":
            await db.execute(
                # FIX: Added col() here to fix Pylance boolean error
                update(User).where(col(User.clerk_user_id) ==
                                   clerk_user_id).values(is_active=False)
            )
            await db.commit()
            return {"success": True}

        # -- Extract Data for Creation/Updating --
        email = None
        email_addresses = getattr(data, "email_addresses", None) or []
        primary_email_id = getattr(data, "primary_email_address_id", None)
        for e in email_addresses:
            if e.id == primary_email_id:
                email = e.email_address
                break

        if not email and email_addresses:
            email = email_addresses[0].email_address

        if not email:
            await db.commit()
            return {"success": True, "message": "No email found, skipped."}

        metadata = getattr(data, "public_metadata", None) or {}
        role_enum = None  # Default to None to prevent downgrades!
        if "role" in metadata:
            try:
                role_enum = UserType(metadata["role"].lower())
            except ValueError:
                pass

        # -- USE THE REUSABLE FUNCTION FOR BOTH CREATE AND UPDATE --
        if validated_event.type in ["user.created", "user.updated"]:
            await upsert_user(
                db=db,
                clerk_id=clerk_user_id,
                email=email,
                first_name=getattr(data, "first_name", "") or "",
                last_name=getattr(data, "last_name", "") or "",
                phone_number="",  # Webhooks usually omit this, frontend provides it via /provision
                role_enum=role_enum
            )

        # 5. COMMIT EVERYTHING
        await db.commit()
        logger.info(f"Successfully processed webhook {validated_event.type}")
        return {"success": True}

    except ValidationError as e:
        await db.rollback()
        logger.error(
            f"Validation error processing clerk webhook: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            f"Database error processing clerk webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
