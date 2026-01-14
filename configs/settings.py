from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings."""

    APP_NAME: str = "ResumeMindAI"
    ENVIRONMENT: str = "development"
    VERSION: str = "0.1.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
