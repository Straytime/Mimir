"""Tests for Jina Reader web_fetch adapter."""

from dataclasses import replace

import httpx
import pytest

from app.application.dto.research import FetchResponse
from app.application.services.invocation import RetryableOperationError
from app.core.config import Settings
from app.infrastructure.providers import build_provider_runtime
from app.infrastructure.research.jina import JinaWebFetchClient
from app.infrastructure.research.local_stub import LocalStubWebFetchClient


# ---------------------------------------------------------------------------
# Factory wiring
# ---------------------------------------------------------------------------


def test_stub_mode_web_fetch_still_uses_stub_adapter() -> None:
    runtime = build_provider_runtime(Settings())
    assert isinstance(runtime.web_fetch_client, LocalStubWebFetchClient)


def test_real_mode_web_fetch_uses_jina_adapter() -> None:
    runtime = build_provider_runtime(
        replace(
            Settings(),
            provider_mode="real",
            zhipu_api_key="zhipu-key",
            jina_api_key="jina-key",
            e2b_api_key="e2b-key",
        )
    )
    assert isinstance(runtime.web_fetch_client, JinaWebFetchClient)


def test_real_web_fetch_mode_missing_jina_api_key_fails_fast() -> None:
    with pytest.raises(ValueError, match="JINA_API_KEY"):
        build_provider_runtime(
            replace(
                Settings(),
                web_fetch_provider_mode="real",
                jina_api_key=None,
            )
        )


# ---------------------------------------------------------------------------
# Jina adapter behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_jina_success_maps_to_fetch_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://r.jina.ai/https://example.com/article"
        assert request.headers["authorization"] == "Bearer jina-key"
        assert request.headers["accept"] == "text/plain"
        return httpx.Response(
            status_code=200,
            text="Article Title\n\nSome interesting content about the topic.",
        )

    adapter = JinaWebFetchClient(
        api_key="jina-key",
        transport=httpx.MockTransport(handler),
    )
    result = await adapter.fetch("https://example.com/article")

    assert isinstance(result, FetchResponse)
    assert result.success is True
    assert result.url == "https://example.com/article"
    assert result.content is not None
    assert "interesting content" in result.content


@pytest.mark.asyncio
async def test_jina_timeout_maps_to_retryable_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    adapter = JinaWebFetchClient(
        api_key="jina-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(RetryableOperationError):
        await adapter.fetch("https://example.com/article")


@pytest.mark.asyncio
async def test_jina_5xx_maps_to_retryable_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=502, text="Bad Gateway")

    adapter = JinaWebFetchClient(
        api_key="jina-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(RetryableOperationError):
        await adapter.fetch("https://example.com/article")


@pytest.mark.asyncio
async def test_jina_4xx_maps_to_explicit_failure() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=404, text="Not Found")

    adapter = JinaWebFetchClient(
        api_key="jina-key",
        transport=httpx.MockTransport(handler),
    )
    result = await adapter.fetch("https://example.com/missing")

    assert result.success is False
    assert result.url == "https://example.com/missing"


@pytest.mark.asyncio
async def test_jina_empty_body_maps_to_explicit_failure() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, text="")

    adapter = JinaWebFetchClient(
        api_key="jina-key",
        transport=httpx.MockTransport(handler),
    )
    result = await adapter.fetch("https://example.com/empty")

    assert result.success is False


@pytest.mark.asyncio
async def test_jina_does_not_leak_api_key_in_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=503, text="Service Unavailable")

    adapter = JinaWebFetchClient(
        api_key="super-secret-jina-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(RetryableOperationError):
        await adapter.fetch("https://example.com/article")

    assert "super-secret-jina-key" not in caplog.text


@pytest.mark.asyncio
async def test_jina_extracts_title_from_first_line() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            text="# My Article Title\n\nBody paragraph here.",
        )

    adapter = JinaWebFetchClient(
        api_key="jina-key",
        transport=httpx.MockTransport(handler),
    )
    result = await adapter.fetch("https://example.com/article")

    assert result.success is True
    assert result.title == "My Article Title"
