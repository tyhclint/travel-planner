from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class DBSettings(BaseSettings):
    environment: str = "development"
    port: int = 8002
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "travel_planner"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_db_settings() -> DBSettings:
    return DBSettings()
