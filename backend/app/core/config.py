from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    SYNC_DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    # CELERY_BROKER_URL: str
    # CELERY_RESULT_BACKEND: str

    # Auth
    SECRET_KEY: str
    DEBUG: bool = False
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 300
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: str = ""

    # Bolna
    BOLNA_API_KEY: str = ""
    BOLNA_BASE_URL: str = "https://api.bolna.dev"
    BOLNA_WEBHOOK_SECRET: str = ""

    # App
    APP_ENV: str = "development"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  

settings = Settings()