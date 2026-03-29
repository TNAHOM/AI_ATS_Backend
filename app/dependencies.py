from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.exceptions import BaseAppException
from app.core.security import clerk_jwt_verifier
from app.models.user import User
from app.schemas.auth import AuthenticatedUser

bearer_scheme = HTTPBearer(auto_error=False)


async def current_active_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_async_session),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise BaseAppException(
            error_code="AUTH_MISSING_BEARER_TOKEN",
            message="Authentication credentials were not provided.",
            status_code=401,
        )

    payload = clerk_jwt_verifier.verify(credentials.credentials)
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise BaseAppException(
            error_code="AUTH_INVALID_SUBJECT",
            message="Invalid authentication token.",
            status_code=401,
        )

    email: str | None = None
    email_claim = payload.get("email")
    if isinstance(email_claim, str):
        email = email_claim

    if email is None:
        email_addresses = payload.get("email_addresses")
        if isinstance(email_addresses, list) and email_addresses:
            first_email = email_addresses[0]
            if isinstance(first_email, str):
                email = first_email
            elif isinstance(first_email, dict):
                nested_email = first_email.get("email_address")
                if isinstance(nested_email, str):
                    email = nested_email

    internal_user_id = None
    is_active = True
    is_superuser = False
    if email is not None:
        result = await db.execute(select(User).where(User.email == email))
        db_user = result.scalar_one_or_none()
        if db_user is not None and not db_user.is_active:
            raise BaseAppException(
                error_code="AUTH_INACTIVE_USER",
                message="User account is inactive.",
                status_code=403,
            )
        if db_user is not None:
            internal_user_id = db_user.id
            is_active = db_user.is_active
            is_superuser = db_user.is_superuser

    return AuthenticatedUser(
        clerk_id=subject,
        email=email,
        internal_user_id=internal_user_id,
        is_active=is_active,
        is_superuser=is_superuser,
    )


async def current_superuser(
    user: AuthenticatedUser = Depends(current_active_user),
) -> AuthenticatedUser:
    if not user.is_superuser:
        raise BaseAppException(
            error_code="AUTH_FORBIDDEN",
            message="Insufficient permissions for this resource.",
            status_code=403,
            details={},
        )
    return user


async def current_provisioned_user(
    user: AuthenticatedUser = Depends(current_active_user),
) -> AuthenticatedUser:
    if user.internal_user_id is None:
        raise BaseAppException(
            error_code="AUTH_USER_NOT_PROVISIONED",
            message="Authenticated user is not provisioned in the backend.",
            status_code=403,
        )
    return user
