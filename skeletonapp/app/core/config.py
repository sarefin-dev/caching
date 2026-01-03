from functools import lru_cache

from fastapi import Depends
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Priority (highest to lowest):
    1. Explicit environment variables
    2. .env file
    3. Default values
    """

    environment: str = "development"
    debug: bool = False

    # Application
    app_name: str = "Payment Service"
    log_level: str = "INFO"

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # external services
    payment_gateway_url: str
    payment_gateway_api_key: str
    payment_gateway_timeout: float = 10.0

    # retry configuration
    max_retries: int = 3
    initial_retry_delay: float = 1.0
    max_retry_delay: float = 30.0
    backoff_multiplier: float = 2.0
    


    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
