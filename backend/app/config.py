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
    anthropic_model_opus: str = "claude-opus-4-6"
    anthropic_model_sonnet: str = "claude-sonnet-4-5-20250929"

    # Infrastructure
    redis_url: str = "redis://localhost:6379"
    database_url: str = "sqlite:///./data/app.db"

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # Integrations
    slack_bot_token: str = ""
    linear_api_key: str = ""

    # Budget
    max_budget_per_session_usd: float = 2.0
    max_turns: int = 30

    @property
    def anthropic_configured(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def slack_configured(self) -> bool:
        return bool(self.slack_bot_token)

    @property
    def linear_configured(self) -> bool:
        return bool(self.linear_api_key)


settings = Settings()
