from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI ATS Backend"
    # This will look for a variable named DB_URL in your .env file
    DB_URL: str
    SECRET_KEY: str
    GEMINI_API_KEY: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    S3_BUCKET_NAME: str
    MAX_JOB_APPLICANT_RETRIES: int = 3

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings() # type: ignore