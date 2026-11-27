from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    gemini_api_key: str = ""

    # Optional Google OAuth.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    public_base_url: str = ""
    cors_allowed_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    expo_access_token: str = ""

    # GitHub coding-agent integration.
    github_token_encryption_key: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = ""

    env: str = "development"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        extra="ignore",
    )


settings = Settings()
