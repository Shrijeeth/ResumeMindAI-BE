from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings."""

    APP_NAME: str = "ResumeMindAI"
    ENVIRONMENT: str = "development"
    VERSION: str = "0.1.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_BASE_URL: str = "http://localhost:8000"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    APP_SECRET: str = ""
    INTERNAL_API_KEY: str = ""
    CORS_ALLOW_ORIGINS: list[str] = ["*"]
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    REDIS_URL: str = ""
    RATE_LIMITER_DEFAULT_LIMITS: list[str] = ["5/30seconds"]
    TRUSTED_PROXIES: list[str] = []
    PROVIDER_TEST_CACHE_TTL_SECONDS: int = 300
    PROVIDER_LIST_CACHE_TTL_SECONDS: int = 60
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = ""
    S3_TEST_FILE_PATH: str = ""
    FALKORDB_HOST: str = ""
    FALKORDB_PORT: int = 6379
    FALKORDB_USERNAME: str = ""
    FALKORDB_PASSWORD: str = ""
    FALKORDB_TEST_GRAPH_NAME: str = "test_graph"

    # GraphRAG settings
    GRAPHRAG_ENABLED: bool = True
    GRAPHRAG_MAX_CONTENT_LENGTH: int = 50000
    GRAPHRAG_EXTRACTION_TIMEOUT: int = 120

    TASKIQ_QUEUE_NAME: str = "resumemind:taskiq:queue"
    TASKIQ_RESULT_TTL_SECONDS: int = 604800

    # Idempotency
    IDEMPOTENCY_TTL_SECONDS: int = 60
    IDEMPOTENCY_LOCK_TTL_SECONDS: int = 10
    IDEMPOTENCY_KEY_PREFIX: str = "idempotency"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
