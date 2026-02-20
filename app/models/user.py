from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from app.core.database import Base

class User(SQLAlchemyBaseUserTableUUID, Base):
    pass