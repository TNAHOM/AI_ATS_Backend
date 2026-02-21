# from fastapi_users.db import SQLAlchemyBaseUserTableUUID
import enum
from fastapi_users_db_sqlmodel import SQLModelBaseUserDB
from sqlmodel import Field

class UserType(str, enum.Enum):
    APPLICANT = "applicant"
    RECRUITER = "recruiter"
    ADMIN = "admin"
class User(SQLModelBaseUserDB, table=True):
    user_type: UserType = Field(default=UserType.APPLICANT)
    first_name: str
    last_name: str
    phone_number: str = Field(max_items=12, min_items=9)
    pass