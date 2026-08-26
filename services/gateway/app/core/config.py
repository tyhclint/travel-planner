from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    environment: str = "development"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "*"]

    # Microservices target URLs
    agent_service_url: str = "http://agent-service:8001"
    db_service_url: str = "http://db-service:8002"
    trip_service_url: str = "http://trip-service:8003"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_gateway_settings() -> GatewaySettings:
    return GatewaySettings()
