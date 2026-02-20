from collections.abc import AsyncGenerator
from fastapi_users_db_sqlmodel import SQLModelUserDatabaseAsync
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
# from sqlalchemy.orm import declarative_base
from app.core.config import settings

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

engine = create_async_engine(settings.DB_URL)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

# Base = declarative_base()

# Get the DB Session
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

# Get the User Database adapter (for FastAPI Users)
async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    from app.models.user import User  # Import here to avoid circular imports
    yield SQLModelUserDatabaseAsync(user_model=User, session=session)

# Optional: Helper for creating tables in dev (in prod use Alembic)
async def create_db_and_tables():
    async with engine.begin() as conn:
        # Use SQLModel metadata instead of Base
        await conn.run_sync(SQLModel.metadata.create_all)