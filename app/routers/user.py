from fastapi import APIRouter
from app.dependencies import fastapi_users

from app.schemas.user import UserRead, UserUpdate

user = APIRouter(
    prefix="/users",
    tags=["users"],
)

user.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)