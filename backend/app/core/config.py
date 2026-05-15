from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import ClassVar

class Settings(BaseSettings):
    APP_NAME: str = "IT Admin Dashboard"

    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    API_V1_PREFIX: str = "/api/v1"

    # Business Central agent
    BC_AGENT_URL: str = "http://1tech-bc:9140"
    BC_AGENT_API_KEY: str = "4fQ8dV9KJwM2GmXy7sAqPZ6bEJkLxR3C0tFhNDUWnYpV5S8rHaQe"
    
    #LDAP Auth
    LDAP_SERVER: str = "ldaps://1tech-dc.1sttech.local"
    LDAP_BASE_DN: str = "DC=1sttech,DC=local"
    LDAP_USER_FILTER: str = "(sAMAccountName={username})"

    JWT_SECRET: str = "replace-with-long-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    
    # Database (not pydantic-managed)
    DB_URL: ClassVar[str] = (
        "sqlite+aiosqlite:////home/administrator/it-admin-dashboard/backend/admindb.sqlite3"
    )

    # ✅ THIS LINE FIXES YOUR CRASH
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",        # ✅ ignore unknown env vars
    )

settings = Settings()