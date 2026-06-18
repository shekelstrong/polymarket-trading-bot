"""Settings loaded from environment variables (and .env)."""

from __future__ import annotations

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Trading
    polygon_wallet_private_key: Optional[str] = None
    polygon_funder_address: Optional[str] = None
    clob_api_url: str = "https://clob.polymarket.com"
    gamma_api_url: str = "https://gamma-api.polymarket.com"
    chain_id: int = Field(default=137, alias="polybot_chain_id")

    # Runtime
    budget_usdc: float = Field(default=100.0, alias="polybot_budget_usdc")
    max_position_usdc: float = Field(default=5.0, alias="polybot_max_position_usdc")
    max_daily_loss_usdc: float = Field(default=25.0, alias="polybot_max_daily_loss_usdc")
    max_daily_loss_usd: float = 25.0  # back-compat alias used by bot.py
    log_level: str = Field(default="INFO", alias="polybot_log_level")
    db_url: str = Field(default="sqlite:///./polybot.db", alias="polybot_db_url")

    # Backend mode
    telegram_bot_token: Optional[str] = Field(default=None, alias="polybot_telegram_bot_token")
    host: str = Field(default="0.0.0.0", alias="polybot_host")
    port: int = Field(default=8080, alias="polybot_port")

    # Optional
    openai_api_key: Optional[str] = None
    news_api_key: Optional[str] = None


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Lazily build a Settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
