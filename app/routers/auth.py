from fastapi import Depends
from app.models.user import User
from app.core.security import auth_backend
from app.schemas.common import MessageData, ResponseEnvelope
from app.schemas.user import UserRead, UserCreate
from app.dependencies import fastapi_users, current_active_user

from fastapi import APIRouter

# from ..dependencies import get_token_header
# responses={404: {"description": "Not found"}}, Depends(get_token_header), etc can add global dependencies, responses, etc. to all routes in this auth
auth = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

# Login and Logout routes are provided by FastAPIUsers
auth.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
    tags=["auth"],
)

# Add the Register Route
auth.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="",
    tags=["auth"],
)

# Add the Verify Route
auth.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/verify",
    tags=["auth"],
)

# Add the Reset Password Route
auth.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

@auth.get(
    "/authenticated-route",
    response_model=ResponseEnvelope[MessageData],
    summary="Get authenticated greeting",
    description="Returns a standardized greeting envelope for an authenticated user.",
)
async def authenticated_route(user: User = Depends(current_active_user)) -> ResponseEnvelope[MessageData]:
    return ResponseEnvelope[MessageData](
        success=True,
        message="Authenticated user fetched successfully.",
        data=MessageData(message=f"Hello {user.email}!"),
    )