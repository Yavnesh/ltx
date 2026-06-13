from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "LTX Video Platform"
    ENVIRONMENT: str = "local"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/ltx_db"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    JWT_SECRET: str = "super-secret-key-change-in-production-1234567890"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Storage
    STORAGE_PROVIDER_TYPE: str = "local"  # local, minio, s3
    STORAGE_LOCAL_PATH: str = "/tmp/ltx_storage"
    STORAGE_ENDPOINT_URL: str | None = None
    STORAGE_ACCESS_KEY: str | None = None
    STORAGE_SECRET_KEY: str | None = None
    STORAGE_BUCKET_NAME: str = "ltx-videos"
    STORAGE_REGION: str = "us-east-1"

    # Video Generator
    GENERATOR_TYPE: str = "mock"  # mock, ltx
    LTX_MODEL_PATH: str = "Lightweight-Diffusion-Models/LTX-Video"

    # Observability
    ENABLE_OTEL: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_SERVICE_NAME: str = "ltx-platform"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Read environment variables directly to override if needed
settings = Settings()
