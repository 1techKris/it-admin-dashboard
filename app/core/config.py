from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "IT Admin Dashboard"
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./test.db"

    AD_SERVER: str | None = None
    AD_USERNAME: str | None = None
    AD_PASSWORD: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()