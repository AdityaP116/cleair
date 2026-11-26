from pydantic_settings import BaseSettings
from typing import List, Optional, Any

class Settings(BaseSettings):
    PROJECT_NAME: str = "Urban Air Quality Assistant (SmogSense)"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/v1"
    
    # Environment
    ENV: str = "development"
    DEBUG: Any = True
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production-uaqa-smogsense"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # Allowed origins
    CORS_ORIGINS: List[str] = ["*"]
    
    # External APIs
    OPEN_METEO_AIR_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    OPEN_METEO_WEATHER_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPENAQ_API_URL: str = "https://api.openaq.org/v3"
    OPENAQ_API_KEY: Optional[str] = None
    DATA_GOV_IN_API_KEY: Optional[str] = None
    
    # LLM Settings
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # Caching & DB
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Rate Limiting
    RATE_LIMIT_MAX_REQUESTS: int = 120
    RATE_LIMIT_WINDOW_SEC: int = 60
    RATE_LIMIT_FAIL_OPEN: bool = True
    TRUSTED_PROXIES: List[str] = ["127.0.0.1"]

    # Contact Form SMTP (optional, configured via .env)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    CONTACT_RECIPIENT_EMAIL: Optional[str] = None
    SITE_BASE_URL: str = "http://127.0.0.1:8000"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
