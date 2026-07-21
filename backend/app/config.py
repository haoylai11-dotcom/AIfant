"""
Application configuration loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = "抖音-快手AI数字人短视频内容分析"
    VERSION: str = "0.1.0"
    RESEARCH_TEAM: str = "Research Team"
    INSTITUTION: str = "Institution"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./dyks_data.db"

    # Security
    SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440

    # File storage
    MEDIA_STORAGE_PATH: str = "./media_storage"

    # Logging
    LOG_LEVEL: str = "INFO"

    # External APIs (Phase 2)
    DOUYIN_CLIENT_KEY: Optional[str] = None
    DOUYIN_CLIENT_SECRET: Optional[str] = None
    KUAISHOU_APP_ID: Optional[str] = None
    KUAISHOU_APP_SECRET: Optional[str] = None

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
