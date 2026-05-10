import os
import logging

from fastapi import Depends, HTTPException, Request, APIRouter
from sqlmodel import col
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from svix.webhooks import Webhook, WebhookVerificationError

from app.core.database import get_async_session
from app.models.event import ProcessedWebhookEvent
from app.models.user import User, UserType
from app.schemas.Clerk.clerk_event import ClerkWebhookEvent
from app.schemas.common import MessageData, ResponseEnvelope
from app.schemas.auth import AuthenticatedUser, ProvisionRequest, VerifiedClerkToken
from app.dependencies import current_active_user, verify_clerk_token
from app.services.users import upsert_user
from pydantic import ValidationError

logger = logging.getLogger(__name__)

auth = APIRouter(prefix="/auth", tags=["auth"])
webhook_router = APIRouter(prefix="/auth/webhooks", tags=["webhooks"])

# ==========================================
# AUTH ENDPOINTS
# ==========================================


@auth.post("/login", response_model=ResponseEnvelope[AuthenticatedUser])
async def login(user: AuthenticatedUser = Depends(current_active_user)):
    return ResponseEnvelope[AuthenticatedUser](
        success=True, message="Login successful.", data=AuthenticatedUser.model_validate(user)
    )


@auth.get("/authenticated-route", response_model=ResponseEnvelope[MessageData])
async def authenticated_route(user: AuthenticatedUser = Depends(current_active_user)):
    return ResponseEnvelope[MessageData](
        success=True, message="Success.", data=MessageData(message=f"Hello {user.email or user.clerk_id}!")
    )


@auth.post("/provision")
async def provision_user(
    body: ProvisionRequest,
    token_data: VerifiedClerkToken = Depends(verify_clerk_token),
    db: AsyncSession = Depends(get_async_session)
):
    logger.info(f"Checking provisioning for user {token_data.email}")
    # metadata = token_data.get("metadata", {})
    # role = metadata.get("role", "applicant").upper()
    # try:
    #     role_enum = UserType(role.lower())
    # except ValueError:
    #     role_enum = UserType.APPLICANT

    # Pass None for role. Let the webhook be the Source of Truth for roles!
    try:
        user = await upsert_user(
            db=db,
            clerk_id=token_data.clerk_id,
            email=token_data.email,
            first_name=body.first_name,
            last_name=body.last_name,
            phone_number=body.phone_number,
            role_enum=None
        )

        await db.commit()

        return {"success": True, "message": "User provisioned successfully", "data": {"id": str(user.id)}}
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error provisioning user: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Database error provisioning user")
# ==========================================
# WEBHOOK ENDPOINTS
# ==========================================


@webhook_router.post("/clerk")
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_async_session)):
    logger.info("Received Clerk webhook request")
    secret = os.getenv("CLERK_WEBHOOK_SECRET")
    if not secret:
        logger.error("CLERK_WEBHOOK_SECRET is not configured")
        raise HTTPException(
            status_code=500, detail="Webhook secret not configured")

    payload = await request.body()
    headers = request.headers

    try:
        wh = Webhook(secret)
        event = wh.verify(payload, dict(headers))
    except WebhookVerificationError as exc:
        logger.error(
            f"Clerk webhook verification failed: {exc}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid signature")

    svix_id = headers.get("svix-id")
    if not svix_id:
        logger.error("Missing svix-id header in webhook")
        raise HTTPException(status_code=400, detail="Missing svix-id header")

    # IDEMPOTENCY
    db.add(ProcessedWebhookEvent(svix_id=svix_id))
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        logger.info(
            f"Webhook {svix_id} already processed. Skipping. Details: {exc}")
        return {"success": True, "message": "Webhook already processed"}

    try:
        validated_event = ClerkWebhookEvent.model_validate(event)
        data = validated_event.data
        clerk_user_id = data.id
        logger.info(
            f"Processing webhook event: {validated_event.type} for clerk_user_id: {clerk_user_id}")

        # 1. Handle Deletion
        if validated_event.type == "user.deleted":
            await db.execute(
                update(User).where(col(User.clerk_user_id) ==
                                   clerk_user_id).values(is_active=False)
            )
            await db.commit()
            return {"success": True}

        # 2. Extract Data for Create/Update
        email = None
        email_addresses = getattr(data, "email_addresses", [])
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

        role = getattr(data, "public_metadata", {}).get("role", "applicant")
        try:
            role_enum = UserType(role.lower())
        except ValueError:
            role_enum = UserType.APPLICANT

        # 3. USE THE REUSABLE FUNCTION for both created and updated!
        if validated_event.type in ["user.created", "user.updated"]:
            await upsert_user(
                db=db,
                clerk_id=clerk_user_id,
                email=email,
                first_name=getattr(data, "first_name", "") or "",
                last_name=getattr(data, "last_name", "") or "",
                phone_number="",  # Webhooks don't cleanly send primary phone easily without extra logic, frontend handles it better
                role_enum=role_enum
            )

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
