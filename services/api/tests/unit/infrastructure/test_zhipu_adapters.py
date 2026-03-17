import json
from types import SimpleNamespace

import httpx
import pytest

from app.application.dto.invocation import (
    LLMInvocation,
    PromptBundle,
    PromptMessage,
)
from app.application.dto.research import PlannerInvocation, SearchResponse
from app.application.invocation_contracts import (
    build_collect_agent_tool_schema,
    build_stage_profile,
)
from app.application.services.invocation import (
    RetryableOperationError,
    RiskControlTriggered,
)
from app.application.services.llm import RetryableLLMError, TextGeneration
from app.core.config import Settings
from app.domain.enums import FreshnessRequirement, OutputFormat
from app.domain.schemas import RequirementDetail
from app.infrastructure.llm.zhipu import ZhipuClarificationGenerator
from app.infrastructure.research.jina import JinaWebFetchClient
from app.infrastructure.research.real_http import ZhipuPlannerAgent, ZhipuWebSearchClient


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


def _build_requirement_detail() -> RequirementDetail:
    return RequirementDetail(
        research_goal="分析中国 AI 搜索产品竞争格局",
        domain="互联网 / AI 产品",
        requirement_details="聚焦中国市场，偏商业分析，覆盖近两年变化。",
        output_format=OutputFormat.BUSINESS_REPORT,
        freshness_requirement=FreshnessRequirement.HIGH,
        language="zh-CN",
    )


@pytest.mark.asyncio
async def test_zhipu_llm_adapter_passes_explicit_profile_and_prompt_bundle() -> None:
    raw_client = FakeZhipuClient(
        response=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="请说明你最关注的竞争维度。")
                )
            ]
        )
    )
    adapter = ZhipuClarificationGenerator(
        client=raw_client,
        natural_model="glm-test",
        options_model="glm-test",
    )

    result = await adapter.generate_natural(
        LLMInvocation(
            profile=build_stage_profile(Settings(), stage="clarification_natural"),
            prompt_bundle=PromptBundle(
                system_prompt=None,
                user_prompt="private prompt",
            ),
        )
    )

    assert isinstance(result, TextGeneration)
    assert result.full_text == "请说明你最关注的竞争维度。"
    call = raw_client.chat.completions.calls[0]
    assert call["model"] == "glm-5"
    assert call["temperature"] == 0.5
    assert call["top_p"] == 0.8
    assert call["max_tokens"] == 98304
    assert call["thinking"] == {"type": "disabled"}
    assert call["stream"] is True
    assert call["messages"] == [{"role": "user", "content": "private prompt"}]
    assert not call.get("tools")


@pytest.mark.asyncio
async def test_zhipu_planner_adapter_uses_prompt_bundle_and_tool_schema_instead_of_prompt_name() -> None:
    raw_client = FakeZhipuClient(
        response=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "reasoning_deltas": ["先补公开资料"],
                                "stop": False,
                                "plans": [
                                    {
                                        "collect_target": "目标 A",
                                        "additional_info": "补充 A",
                                        "freshness_requirement": "high",
                                    }
                                ],
                            },
                            ensure_ascii=False,
                        )
                    )
                )
            ]
        )
    )
    adapter = ZhipuPlannerAgent(client=raw_client, model="glm-test")

    decision = await adapter.plan(
        PlannerInvocation(
            prompt_name="planner_round",
            requirement_detail=_build_requirement_detail(),
            summaries=(),
            call_index=1,
            collect_agent_calls_used=0,
            now=SimpleNamespace(isoformat=lambda: "2026-03-16T15:00:00+00:00"),
            profile=build_stage_profile(Settings(), stage="planner"),
            prompt_bundle=PromptBundle(
                system_prompt="system-visible-planner",
                user_prompt="user-visible-planner",
                transcript=(
                    PromptMessage(
                        role="tool",
                        name="collect_agent",
                        tool_call_id="call_1",
                        content='{"collect_target":"历史目标"}',
                    ),
                ),
            ),
            tool_schemas=(build_collect_agent_tool_schema(),),
        )
    )

    assert decision.plans[0].collect_target == "目标 A"
    call = raw_client.chat.completions.calls[0]
    assert call["model"] == "glm-5"
    assert call["temperature"] == 1
    assert call["top_p"] == 1
    assert call["max_tokens"] == 98304
    assert call["thinking"] == {"type": "enabled", "clear_thinking": False}
    assert call["stream"] is True
    assert [message["role"] for message in call["messages"]] == ["system", "user", "tool"]
    assert call["messages"][0]["content"] == "system-visible-planner"
    assert call["messages"][1]["content"].startswith("user-visible-planner")
    assert "请输出合法 JSON" in call["messages"][1]["content"]
    assert call["messages"][2]["tool_call_id"] == "call_1"
    assert call["messages"][2]["name"] == "collect_agent"
    assert all("planner_round" not in message["content"] for message in call["messages"])
    assert call["tools"][0]["function"]["name"] == "collect_agent"
    assert set(call["tools"][0]["function"]["parameters"]["properties"]) == {
        "collect_target",
        "additional_info",
        "freshness_requirement",
    }


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
        await adapter.generate_natural(
            LLMInvocation(
                profile=build_stage_profile(Settings(), stage="clarification_natural"),
                prompt_bundle=PromptBundle(system_prompt=None, user_prompt="private prompt"),
            )
        )


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
        await adapter.generate_natural(
            LLMInvocation(
                profile=build_stage_profile(Settings(), stage="clarification_natural"),
                prompt_bundle=PromptBundle(system_prompt=None, user_prompt="private prompt"),
            )
        )

    assert "secret-key" not in caplog.text
    assert "private prompt" not in caplog.text


@pytest.mark.asyncio
async def test_web_search_uses_fixed_provider_contract_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path.endswith("/web_search")
        assert json.loads(request.content) == {
            "search_engine": "search_prime",
            "query_rewrite": False,
            "count": 10,
            "search_query": "智谱 AI 搜索",
            "search_recency_filter": "noLimit",
        }
        return httpx.Response(
            status_code=200,
            json={
                "search_result": [
                    {
                        "title": "智谱 AI 搜索进展",
                        "link": "https://example.com/news",
                        "content": "发布了新的联网搜索能力。",
                        "icon": "https://example.com/icon.png",
                        "media": "example",
                    }
                ]
            },
        )

    adapter = ZhipuWebSearchClient(
        api_key="secret-key",
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        transport=httpx.MockTransport(handler),
    )

    result = await adapter.search("智谱 AI 搜索", "nolimit")

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
async def test_jina_web_fetch_uses_reader_get_contract_and_truncates_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "https://r.jina.ai/https://example.com/article"
        assert request.headers["Authorization"] == "Bearer secret-key"
        assert request.headers["Accept"] == "text/plain"
        return httpx.Response(
            status_code=200,
            text="# 标题\n\n" + ("a" * 12050),
        )

    adapter = JinaWebFetchClient(
        api_key="secret-key",
        base_url="https://r.jina.ai/",
        transport=httpx.MockTransport(handler),
    )

    result = await adapter.fetch("https://example.com/article")

    assert result.success is True
    assert result.title == "标题"
    assert result.content is not None
    assert len(result.content) == 10000


@pytest.mark.asyncio
async def test_jina_web_fetch_maps_timeout_to_retryable_operation_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    adapter = JinaWebFetchClient(
        api_key="secret-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RetryableOperationError):
        await adapter.fetch("https://example.com/article")
