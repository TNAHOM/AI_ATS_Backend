from fastapi import APIRouter, Depends
from app.core.database import get_async_session
from app.dependencies import fastapi_users, current_active_user

from app.schemas.common import ResponseEnvelope
from app.schemas.user import UserRead, UserUpdate
from app.services import users
from app.models.user import User, UserType
from sqlalchemy.ext.asyncio import AsyncSession


user = APIRouter(
    prefix="/users",
    tags=["users"],
)

@user.get(
    "/all",
    response_model=ResponseEnvelope[list[UserRead]],
    summary="Get all users",
    description="Returns a list of all users in the system.",
)
async def get_all_users(
    skip: int = 0,
    limit: int = 50,
    user_type: UserType | None = None,
    is_verified: bool | None = None,
    is_active: bool | None = None,
    is_superuser: bool | None = None,
    _current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> ResponseEnvelope[list[UserRead]]:
    users_list = await users.get_all_users(
        db=db,
        skip=skip,
        limit=limit,
        user_type=user_type,
        is_verified=is_verified,
        is_active=is_active,
        is_superuser=is_superuser,
    )

    return ResponseEnvelope[list[UserRead]](
        success=True,
        message="Users retrieved successfully.",
        data=[UserRead.model_validate(user_item) for user_item in users_list],
    )


user.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="",
    tags=["users"],
)