import uuid

from app.services.users import get_user_manager
from app.core.security import auth_backend
from app.models.user import User
from fastapi_users import FastAPIUsers
    
    
# Initialize FastAPIUsers with your Manager and Auth Backend
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)