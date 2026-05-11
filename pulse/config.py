"""Application configuration — single source of truth for all environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://pulse:pulse@localhost:5432/pulse"

    # YouTube Data API v3
    youtube_api_key: str = ""

    # Telegram
    telegram_bot_token: str = ""

    # DeepSeek LLM (OpenAI-compatible)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    # YouTube cookies file (Netscape format)
    youtube_cookies_file: str = ""

    # SOCKS5 proxy for YouTube requests (bypasses IP blocks via Tor — runs in same container)
    youtube_proxy: str = "socks5://127.0.0.1:9050"

    # Scheduler interval
    poll_interval_minutes: int = 10

    log_level: str = "INFO"


settings = Settings()
