from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from app.core.config import settings

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlmodel import SQLModel

engine = create_async_engine(settings.DB_URL)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()

async def init_db():
    SQLModel.metadata.create_all(bind=engine)

# Get the DB Session
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

# Get the User Database adapter (for FastAPI Users)
async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    from app.models.user import User  # Import here to avoid circular imports
    yield SQLAlchemyUserDatabase(session, User)

# Optional: Helper for creating tables in dev (in prod use Alembic)
async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
