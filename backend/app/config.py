"""Application configuration via pydantic-settings.

Reads from environment variables and .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # Infrastructure
    redis_url: str = "redis://localhost:6379"
    database_url: str = "sqlite:///./data/app.db"

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # Integrations
    slack_bot_token: str = ""
    linear_api_key: str = ""

    @property
    def anthropic_configured(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
