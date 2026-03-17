from types import SimpleNamespace

import httpx
import pytest

from app.application.dto.research import SearchResponse
from app.application.services.invocation import (
    RetryableOperationError,
    RiskControlTriggered,
)
from app.application.services.llm import RetryableLLMError, TextGeneration
from app.infrastructure.llm.zhipu import ZhipuClarificationGenerator
from app.infrastructure.research.real_http import HttpWebFetchClient, ZhipuWebSearchClient


class FakeChatCompletionsAPI:
    def __init__(self, *, response: object | None = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._response


class FakeZhipuClient:
    def __init__(self, *, response: object | None = None, error: Exception | None = None) -> None:
        self.chat = SimpleNamespace(
            completions=FakeChatCompletionsAPI(response=response, error=error)
        )


class FakeStatusError(Exception):
    def __init__(self, *, status_code: int, body: dict[str, object]) -> None:
        super().__init__(f"status={status_code}")
        self.status_code = status_code
        self.body = body


@pytest.mark.asyncio
async def test_zhipu_llm_adapter_maps_success_to_text_generation() -> None:
    adapter = ZhipuClarificationGenerator(
        client=FakeZhipuClient(
            response=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="请说明你最关注的竞争维度。")
                    )
                ]
            )
        ),
        model="glm-test",
    )

    result = await adapter.generate_natural("private prompt")

    assert isinstance(result, TextGeneration)
    assert result.full_text == "请说明你最关注的竞争维度。"
    assert result.deltas == ("请说明你最关注的竞争维度。",)


@pytest.mark.asyncio
async def test_zhipu_llm_adapter_maps_risk_control_code_1301() -> None:
    adapter = ZhipuClarificationGenerator(
        client=FakeZhipuClient(
            error=FakeStatusError(
                status_code=400,
                body={"error": {"code": "1301", "message": "risk"}},
            )
        ),
        model="glm-test",
    )

    with pytest.raises(RiskControlTriggered):
        await adapter.generate_natural("private prompt")


@pytest.mark.asyncio
async def test_zhipu_llm_adapter_maps_retryable_failures_without_leaking_secret_or_prompt(
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter = ZhipuClarificationGenerator(
        client=FakeZhipuClient(
            error=FakeStatusError(
                status_code=503,
                body={"error": {"code": "server_busy", "message": "temporary"}},
            )
        ),
        model="glm-test",
        api_key_hint="secret-key",
    )

    with pytest.raises(RetryableLLMError):
        await adapter.generate_natural("private prompt")

    assert "secret-key" not in caplog.text
    assert "private prompt" not in caplog.text


@pytest.mark.asyncio
async def test_web_search_maps_success_response_to_search_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/web_search")
        return httpx.Response(
            status_code=200,
            json={
                "search_result": [
                    {
                        "title": "智谱 AI 搜索进展",
                        "link": "https://example.com/news",
                        "content": "发布了新的联网搜索能力。",
                    }
                ]
            },
        )

    adapter = ZhipuWebSearchClient(
        api_key="secret-key",
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        transport=httpx.MockTransport(handler),
    )

    result = await adapter.search("智谱 AI 搜索", "noLimit")

    assert isinstance(result, SearchResponse)
    assert result.query == "智谱 AI 搜索"
    assert result.recency_filter == "noLimit"
    assert result.results[0].title == "智谱 AI 搜索进展"


@pytest.mark.asyncio
async def test_web_search_maps_risk_control_code_1301() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=400,
            json={"error": {"code": "1301", "message": "risk"}},
        )

    adapter = ZhipuWebSearchClient(
        api_key="secret-key",
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RiskControlTriggered):
        await adapter.search("query", "noLimit")


@pytest.mark.asyncio
async def test_web_search_maps_non_risk_failures_to_retryable_operation_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=503, json={"error": {"message": "busy"}})

    adapter = ZhipuWebSearchClient(
        api_key="secret-key",
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RetryableOperationError):
        await adapter.search("query", "noLimit")


@pytest.mark.asyncio
async def test_web_fetch_returns_explicit_failure_for_non_text_content() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={"content-type": "image/png"},
            content=b"\x89PNG\r\n",
        )

    adapter = HttpWebFetchClient(
        transport=httpx.MockTransport(handler),
    )

    result = await adapter.fetch("https://example.com/chart.png")

    assert result.success is False
    assert result.title is None
    assert result.content is None


@pytest.mark.asyncio
async def test_web_fetch_maps_timeout_to_retryable_operation_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    adapter = HttpWebFetchClient(
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RetryableOperationError):
        await adapter.fetch("https://example.com/article")
