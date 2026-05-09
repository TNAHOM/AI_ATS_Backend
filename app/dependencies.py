from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.core.database import get_async_session
from app.core.exceptions import BaseAppException
from app.core.security import clerk_jwt_verifier
from app.models.user import User
from app.schemas.auth import AuthenticatedUser, VerifiedClerkToken

bearer_scheme = HTTPBearer(auto_error=False)


# 1. Create a dependency that ONLY verifies the token (used for provisioning)
async def verify_clerk_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> VerifiedClerkToken:

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise BaseAppException(
            error_code="AUTH_MISSING_BEARER_TOKEN",
            message="Authentication credentials were not provided.",
            status_code=401,
        )

    payload = await clerk_jwt_verifier.verify(credentials.credentials)

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise BaseAppException(error_code="AUTH_INVALID_SUBJECT",
                               message="Invalid authentication token.", status_code=401)

    email: str | None = payload.get("email")
    if email is None:
        email_addresses = payload.get("email_addresses")
        if isinstance(email_addresses, list) and email_addresses:
            first_email = email_addresses[0]
            if isinstance(first_email, str):
                email = first_email
            elif isinstance(first_email, dict):
                email = first_email.get("email_address")

    if email is None:
        raise BaseAppException(error_code="AUTH_MISSING_EMAIL_CLAIM",
                               message="Token is missing email claim.", status_code=401)

    return VerifiedClerkToken(
        clerk_id=subject,
        email=email,
        metadata=payload.get("metadata", {})
    )


# 2. Update existing dependency to use the verified token
async def current_active_user(
    token_data: VerifiedClerkToken = Depends(verify_clerk_token),
    db: AsyncSession = Depends(get_async_session),
) -> AuthenticatedUser:

    # FIX 3: Query by clerk_user_id instead of email
    result = await db.execute(select(User).where(col(User.clerk_user_id) == token_data.clerk_id))
    db_user = result.scalar_one_or_none()

    if db_user is None:
        raise BaseAppException(
            error_code="AUTH_USER_NOT_PROVISIONED",
            message="Authenticated user is not provisioned in the backend.",
            status_code=403,
        )
    if not db_user.is_active:
        raise BaseAppException(
            error_code="AUTH_INACTIVE_USER",
            message="User account is inactive.",
            status_code=403,
        )

    return AuthenticatedUser(
        clerk_id=token_data.clerk_id,
        email=token_data.email,
        internal_user_id=db_user.id,
        is_active=db_user.is_active,
        is_superuser=db_user.is_superuser,
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
