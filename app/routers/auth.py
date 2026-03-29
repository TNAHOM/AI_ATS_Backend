from fastapi import Depends
from app.schemas.common import MessageData, ResponseEnvelope
from app.schemas.auth import AuthenticatedUser
from app.dependencies import current_active_user

from fastapi import APIRouter

# from ..dependencies import get_token_header
# responses={404: {"description": "Not found"}}, Depends(get_token_header), etc can add global dependencies, responses, etc. to all routes in this auth
auth = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

@auth.get(
    "/authenticated-route",
    response_model=ResponseEnvelope[MessageData],
    summary="Get authenticated greeting",
    description="Returns a standardized greeting envelope for an authenticated user.",
)
async def authenticated_route(user: AuthenticatedUser = Depends(current_active_user)) -> ResponseEnvelope[MessageData]:
    user_identifier = user.email or user.id
    return ResponseEnvelope[MessageData](
        success=True,
        message="Authenticated user fetched successfully.",
        data=MessageData(message=f"Hello {user_identifier}!"),
    )
