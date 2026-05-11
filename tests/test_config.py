"""Tests for application configuration loading."""

from pulse.config import Settings


def test_settings_default_values() -> None:
    settings = Settings()
    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.ollama_model == "qwen2.5:7b"
    assert settings.ollama_embed_model == "nomic-embed-text"
    assert settings.llm_provider == "ollama"


def test_database_url_uses_asyncpg_driver() -> None:
    settings = Settings()
    assert "asyncpg" in settings.database_url


def test_siyuan_api_url_default() -> None:
    settings = Settings()
    assert settings.siyuan_api_url == "https://note.rebdev.online"


def test_settings_is_singleton() -> None:
    from pulse.config import settings as s1
    from pulse.config import settings as s2
    assert s1 is s2