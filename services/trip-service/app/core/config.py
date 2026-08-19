from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class TripServiceSettings(BaseSettings):
    environment: str = "development"
    port: int = 8003
    enable_live_scraping: bool = False
    trip_com_base_url: str = "https://www.trip.com"
    request_timeout: float = 15.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_trip_settings() -> TripServiceSettings:
    return TripServiceSettings()
