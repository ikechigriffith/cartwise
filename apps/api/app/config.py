from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]
API_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT_DIR / ".env", API_DIR / ".env"), extra="ignore")

    database_url: str
    redis_url: str = "redis://redis:6379/0"
    environment: str = "development"

    pricesmart_username: str | None = None
    pricesmart_password: str | None = None
    jta_username: str | None = None
    jta_password: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
