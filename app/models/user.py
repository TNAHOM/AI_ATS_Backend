# from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlmodel import SQLModelBaseUserDB

class User(SQLModelBaseUserDB, table=True):
    pass