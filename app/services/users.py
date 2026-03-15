import uuid

from fastapi import status
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BaseAppException
from app.models.user import User
from app.models.user import UserType
from app.core.database import get_user_db

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY
    
    # can create a functions to validate password strength, etc.

    async def on_after_register(self, user: User, request: Request | None = None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Request | None = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")

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
        raise BaseAppException(
            error_code="USER_LIST_FAILED",
            message="Could not retrieve users.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc