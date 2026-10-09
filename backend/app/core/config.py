from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "QueueSense"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "queuesense"
    DATABASE_URL: str | None = None

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # JWT & Auth
    SECRET_KEY: str = "supersecretjwtkeyforqueuesensecanteeenwaittime2024!#$%"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Vision Integration
    VISION_API_KEY: str = "vision-secret-api-key-2024"
    CROWD_STALE_SECONDS: int = 30

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v  # type: ignore
        return ["*"]

    # Rate Limiting
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 15
    RATE_LIMIT_ORDER_PER_MINUTE: int = 30

    # ML & Simulation
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MODEL_REGISTRY_PATH: str = "ml_models"
    MIN_RETRAIN_ROWS: int = 500
    DEFAULT_STATION_DEMAND: dict[str, float] = {
        "tea": 0.45,
        "tawa": 0.35,
        "fryer": 0.20,
    }

    # Prometheus
    PROMETHEUS_METRICS_PATH: str = "/metrics"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow",
    )

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
