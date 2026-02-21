from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import create_db_and_tables, get_async_session
from app.routers import auth, user

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This is where you would put startup logic
    yield
    # This is where you would put shutdown logic
    

# TODO: in the future Depends(get_query_token)
app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
app.include_router(auth.auth)
app.include_router(user.user)
# app.include_router(job.job)

@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()

@app.get("/")
def read_root():
    return {"message": "Welcome to my FastAPI app!"}

@app.get("/db-test")
def test_db(db: AsyncSession = Depends(get_async_session)):
    return {"status": "Database connection is active"}