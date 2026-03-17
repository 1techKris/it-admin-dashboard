# backend/app/core/config.py

from pydantic_settings import BaseSettings
from typing import ClassVar
import os

class Settings(BaseSettings):
    APP_NAME: str = "IT Admin Dashboard"

    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    API_V1_PREFIX: str = "/api/v1"

    # Example existing settings (keep whatever you already have here)
    # SECRET_KEY: str = "your-secret"
    # DEBUG: bool = True

    # IMPORTANT:
    # DB_URL is NOT a Pydantic field — mark it as ClassVar so pydantic ignores it.
    DB_URL: ClassVar[str] = (
        "sqlite+aiosqlite:////home/administrator/it-admin-dashboard/backend/admindb.sqlite3"
    )

settings = Settings()