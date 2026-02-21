import uuid
from fastapi_users import schemas
from app.models.user import UserType

class UserRead(schemas.BaseUser[uuid.UUID]):
    user_type: UserType
    class Config:
        from_attributes = True


class UserCreate(schemas.BaseUserCreate):
    user_type: UserType
    class Config:
        from_attributes = True


class UserUpdate(schemas.BaseUserUpdate):
    user_type: UserType
    class Config:
        from_attributes = True