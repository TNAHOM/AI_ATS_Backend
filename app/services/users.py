import uuid

from fastapi import status
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col
import logging

from app.core.config import settings
from app.core.exceptions import BaseAppException
from app.models.user import User
from app.models.user import UserType
from app.core.database import get_user_db

logger = logging.getLogger(__name__)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY

    # can create a functions to validate password strength, etc.

    async def on_after_register(self, user: User, request: Request | None = None):
        logger.info(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ):
        logger.info(
            f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Request | None = None
    ):
        logger.info(
            f"Verification requested for user {user.id}. Verification token: {token}")

# This is the dependency you will actually use in your routes


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


async def get_all_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    user_type: UserType | None = None,
    is_verified: bool | None = None,
    is_active: bool | None = None,
    is_superuser: bool | None = None,
) -> list[User]:
    try:
        logger.info(
            f"Fetching users (skip={skip}, limit={limit}, user_type={user_type})")
        query = select(User)

        if user_type is not None:
            query = query.where(getattr(User, "user_type") == user_type)
        if is_verified is not None:
            query = query.where(getattr(User, "is_verified") == is_verified)
        if is_active is not None:
            query = query.where(getattr(User, "is_active") == is_active)
        if is_superuser is not None:
            query = query.where(getattr(User, "is_superuser") == is_superuser)

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    except SQLAlchemyError as exc:
        logger.error("Database error retrieving users: %s", exc, exc_info=True)
        raise BaseAppException(
            error_code="USER_LIST_FAILED",
            message="Could not retrieve users.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


async def upsert_user(
    db: AsyncSession,
    clerk_id: str,
    email: str,
    first_name: str,
    last_name: str,
    phone_number: str,
    role_enum: UserType | None = None
) -> User:
    """Creates a user if they don't exist, updates them if they do."""
    logger.info(f"Upserting user: {email} (clerk_id={clerk_id})")
    result = await db.execute(select(User).where(col(User.clerk_user_id) == clerk_id))
    db_user = result.scalar_one_or_none()

    if db_user:
        # 1. Update standard fields
        db_user.email = email
        if first_name:
            db_user.first_name = first_name
        if last_name:
            db_user.last_name = last_name
        if phone_number:
            db_user.phone_number = phone_number

        # PREVENT ROLE DOWNGRADE: Only update if explicitly provided
        if role_enum is not None:
            db_user.user_type = role_enum
            db_user.is_superuser = (role_enum == UserType.ADMIN)
        return db_user
    else:
        # Create new user (Fallback to applicant if no role provided)
        final_role = role_enum if role_enum is not None else UserType.APPLICANT
        new_user = User(
            id=uuid.uuid4(),
            clerk_user_id=clerk_id,
            email=email,
            hashed_password="clerk_managed",
            is_active=True,
            is_superuser=(final_role == UserType.ADMIN),
            is_verified=True,
            user_type=final_role,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number
        )
        db.add(new_user)
        try:
            await db.flush()
            return new_user
        except IntegrityError as exc:
            await db.rollback()
            logger.error(
                "Integrity error while creating user, likely created concurrently. Details: %s", exc, exc_info=True)
            # Fetch the user the other process just created
            result = await db.execute(select(User).where(col(User.clerk_user_id) == clerk_id))
            return result.scalar_one()
