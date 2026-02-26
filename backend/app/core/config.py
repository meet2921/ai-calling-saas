from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SYNC_DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    DEBUG: bool = False
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: str = ""
    


    class Config:
        env_file = ".env"

settings = Settings()
