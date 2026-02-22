import uuid
from fastapi_users import schemas
from sqlmodel import Field
from app.models.user import UserType

class UserRead(schemas.BaseUser[uuid.UUID]):
    user_type: UserType
    first_name: str
    last_name: str
    phone_number: str = Field(max_items=12, min_items=9)
    class Config:
        from_attributes = True


class UserCreate(schemas.BaseUserCreate):
    user_type: UserType
    first_name: str
    last_name: str
    phone_number: str = Field(max_items=12, min_items=9)
    class Config:
        from_attributes = True


class UserUpdate(schemas.BaseUserUpdate):
    user_type: UserType
    first_name: str
    last_name: str
    phone_number: str = Field(max_items=12, min_items=9)
    class Config:
        from_attributes = True