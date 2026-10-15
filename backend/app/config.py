
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Absolute path to the backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Default SQLite database inside the backend folder
DEFAULT_DATABASE_URL = f"sqlite:///{BACKEND_DIR / 'smart_event.db'}"


class Settings(BaseSettings):
    app_name: str = "SmartEvent"

    # Can be overridden through the DATABASE_URL environment variable
    database_url: str = DEFAULT_DATABASE_URL

    # Set SECRET_KEY in your .env file for secure JWT authentication
    secret_key: str = "change-this-secret-key"

    algorithm: str = "HS256"

    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()

