"""Tests for JINA_API_KEY being optional in real web_fetch mode."""

from dataclasses import replace

from app.core.config import Settings


def test_real_web_fetch_mode_allows_empty_jina_key() -> None:
    """web_fetch_mode=real with jina_api_key=None should not raise."""
    settings = replace(
        Settings(),
        web_fetch_provider_mode="real",
        jina_api_key=None,
    )
    # Must not raise ValueError
    settings.validate_provider_configuration()


def test_real_web_fetch_mode_with_jina_key() -> None:
    """web_fetch_mode=real with jina_api_key set should not raise."""
    settings = replace(
        Settings(),
        web_fetch_provider_mode="real",
        jina_api_key="some-key",
    )
    settings.validate_provider_configuration()
