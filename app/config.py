from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # ===========================================
    # Database
    # ===========================================
    POSTGRES_USER: str = "innostatus"
    POSTGRES_PASSWORD: str = "innostatus_password"
    POSTGRES_DB: str = "innostatus_db"
    DATABASE_URL: str = "postgresql://innostatus:innostatus@postgres:5432/innostatus_db"

    # ===========================================
    # JWT Settings
    # ===========================================
    SECRET_KEY: str = "your-super-secret-key-change-in-production-min-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # ===========================================
    # External Check API - Fragment (бесплатно, текст)
    # ===========================================
    CHECK_FRAGMENT_API_KEY: Optional[str] = None
    CHECK_FRAGMENT_API_URL: str = "https://api.signature-search.ru/api/check_fragment"
    INTEGRATOR_ID: str = "NO VENDOR"
    
    # ===========================================
    # External Check API - Files (платно, файлы)
    # ===========================================
    CHECK_FILES_API_KEY: Optional[str] = None
    CHECK_FILES_API_URL: str = "https://api.inostatus.ru/api"
    
    # Лимиты
    MAX_TEXT_LENGTH_FREE: int = 3000
    MAX_TEXT_LENGTH_PROFILE: int = 20000
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: str = "pdf,txt,docx"

    # ===========================================
    # SMTP Email Settings (MailDev для разработки)
    # ===========================================
    SMTP_HOST: str = "maildev"
    SMTP_PORT: int = 1025
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "noreply@inostatus.local"
    SEND_EMAIL: str = "noreply@inostatus.local"

    # ===========================================
    # Application Settings
    # ===========================================
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"
    DEBUG: bool = False

    # ===========================================
    # Rate Limiting
    # ===========================================
    RATE_LIMIT_PER_MINUTE: int = 60
    DISABLE_RATE_LIMIT: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
