from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    port: int = 8001
    openai_api_key: str | None = None

    # Downstream microservices URLs
    trip_service_url: str = "http://trip-service:8003"
    db_service_url: str = "http://db-service:8002"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
