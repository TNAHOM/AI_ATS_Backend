from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI ATS Backend"
    # This will look for a variable named DB_URL in your .env file
    DB_URL: str
    SECRET_KEY: str
    GEMINI_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings() # type: ignore