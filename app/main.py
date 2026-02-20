from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_async_session
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


@app.get("/")
def read_root():
    return {"message": "Welcome to my FastAPI app!"}

@app.get("/db-test")
def test_db(db: Session = Depends(get_async_session)):
    # This route checks if the database connection is working
    return {"status": "Database connection is active"}