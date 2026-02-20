from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI ATS Backend"
    # This will look for a variable named DB_URL in your .env file
    DB_URL: str = "postgresql+asyncpg://postgres:243313@localhost:5432/AI_ATS"
    SECRET_KEY: str  = "changeme"  # TODO: Override via .env in production

    class Config:
        env_file = ".env"

settings = Settings()