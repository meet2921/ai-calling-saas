from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str
    SYNC_DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # App
    APP_NAME:     str = "MyApp"
    APP_ENV:      str = "development"
    DEBUG:        bool = False
    FRONTEND_URL: str = "https://app.example.com"

    # Auth
    SECRET_KEY:                  str
    JWT_ALGORITHM:               str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 300
    REFRESH_TOKEN_EXPIRE_DAYS:   int = 7
    ALLOWED_ORIGINS:             str = "http://localhost:3000"

    # Bolna
    BOLNA_API_KEY:        str = ""
    BOLNA_BASE_URL:       str = "https://api.bolna.dev"
    BOLNA_WEBHOOK_SECRET: str = ""

    # SMTP
    SMTP_HOST:       str  = "smtp.sendgrid.net"
    SMTP_PORT:       int  = 587
    SMTP_USER:       str  = "apikey"
    SMTP_PASSWORD:   str  = ""
    SMTP_FROM_EMAIL: str  = "noreply@example.com"
    SMTP_FROM_NAME:  str  = "MyApp"
    SMTP_TLS:        bool = False
    SMTP_STARTTLS:   bool = True

    PASSWORD_RESET_EXPIRE_HOURS: int = 24


settings = Settings()