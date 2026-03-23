import json
from types import SimpleNamespace

import httpx
import pytest

from app.application.dto.invocation import (
    LLMInvocation,
    PromptBundle,
    PromptMessage,
)
from app.application.dto.delivery import (
    OutlineSection,
    ResearchOutline,
    WriterInvocation,
)
from app.application.dto.research import CollectorInvocation, PlannerInvocation, SearchResponse
from app.application.invocation_contracts import (
    build_collect_agent_tool_schema,
    build_python_interpreter_tool_schema,
    build_stage_profile,
    build_web_fetch_tool_schema,
    build_web_search_tool_schema,
)
from app.application.services.invocation import (
    RetryableOperationError,
    RiskControlTriggered,
)
from app.application.services.llm import RetryableLLMError, TextGeneration
from app.core.config import Settings
from app.domain.enums import FreshnessRequirement, OutputFormat
from app.domain.schemas import CollectPlan, RequirementDetail
from app.infrastructure.llm.zhipu import (
    ZhipuClarificationGenerator,
    ZhipuChatClient,
    ZhipuCompletionResult,
    _extract_response_with_diagnostics,
    _extract_stream_with_diagnostics,
    _safe_repr,
)
from app.infrastructure.research.jina import JinaWebFetchClient
from app.infrastructure.research.real_http import (
    ZhipuCollectorAgent,
    ZhipuPlannerAgent,
    ZhipuWebSearchClient,
)
from app.infrastructure.delivery.zhipu import ZhipuWriterAgent


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


class RaisingStreamResponse:
    def __iter__(self):
        return self

    def __next__(self):
        raise httpx.ReadTimeout("timed out while streaming")


def _build_requirement_detail() -> RequirementDetail:
    return RequirementDetail(
        research_goal="分析中国 AI 搜索产品竞争格局",
        domain="互联网 / AI 产品",
        requirement_details="聚焦中国市场，偏商业分析，覆盖近两年变化。",
        output_format=OutputFormat.BUSINESS_REPORT,
        freshness_requirement=FreshnessRequirement.HIGH,
        language="zh-CN",
    )


def _build_writer_invocation() -> WriterInvocation:
    return WriterInvocation(
        prompt_name="writer_round",
        requirement_detail=_build_requirement_detail(),
        formatted_sources=(),
        outline=ResearchOutline(
            title="中国 AI 搜索产品竞争格局研究",
            sections=(
                OutlineSection(
                    section_id="section_1",
                    title="研究背景",
                    description="界定研究边界。",
                    order=1,
                ),
            ),
            entities=("AI 搜索",),
        ),
        now=SimpleNamespace(isoformat=lambda: "2026-03-16T15:00:00+00:00"),
        profile=build_stage_profile(Settings(), stage="writer"),
        prompt_bundle=PromptBundle(
            system_prompt="writer-system",
            user_prompt="writer-user",
        ),
        tool_schemas=(build_python_interpreter_tool_schema(),),
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
    assert call["messages"][1]["content"] == "user-visible-planner"
    assert "请输出合法 JSON" not in call["messages"][1]["content"]
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
async def test_zhipu_collector_adapter_returns_tool_calls_with_reasoning_and_prd_schema() -> None:
    raw_client = FakeZhipuClient(
        response=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="tool_calls",
                    message=SimpleNamespace(
                        content="",
                        reasoning_content="先做最近一周搜索。",
                        tool_calls=[
                            SimpleNamespace(
                                id="call_search_1",
                                function=SimpleNamespace(
                                    name="web_search",
                                    arguments='{"search_query":"中国 AI 搜索 产品 2026","search_recency_filter":"oneWeek"}',
                                ),
                            )
                        ],
                    ),
                )
            ]
        )
    )
    adapter = ZhipuCollectorAgent(client=raw_client, model="glm-test")

    decision = await adapter.plan(
        CollectorInvocation(
            prompt_name="collector_round",
            subtask_id="sub_1",
            plan=CollectPlan(
                tool_call_id="call_collect_1",
                revision_id="rev_1",
                collect_target="收集主要玩家",
                additional_info="优先官方与高可信媒体。",
                freshness_requirement=FreshnessRequirement.HIGH,
            ),
            call_index=1,
            tool_call_limit=10,
            now=SimpleNamespace(isoformat=lambda: "2026-03-16T15:00:00+00:00"),
            profile=build_stage_profile(Settings(), stage="collector"),
            prompt_bundle=PromptBundle(
                system_prompt="collector-system",
                user_prompt="collector-user",
            ),
            tool_schemas=(
                build_web_search_tool_schema(),
                build_web_fetch_tool_schema(),
            ),
        )
    )

    assert decision.stop is False
    assert decision.reasoning_text == "先做最近一周搜索。"
    assert decision.provider_finish_reason == "tool_calls"
    assert len(decision.tool_calls) == 1
    assert decision.tool_calls[0].tool_call_id == "call_search_1"
    assert decision.tool_calls[0].tool_name == "web_search"
    assert decision.tool_calls[0].arguments_json == {
        "search_query": "中国 AI 搜索 产品 2026",
        "search_recency_filter": "oneWeek",
    }
    call = raw_client.chat.completions.calls[0]
    assert call["thinking"] == {"type": "enabled", "clear_thinking": False}
    assert call["tools"][0]["function"]["parameters"]["properties"][
        "search_recency_filter"
    ]["enum"] == ["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"]


@pytest.mark.asyncio
async def test_zhipu_collector_adapter_parses_stop_json_into_collect_result_items() -> None:
    raw_client = FakeZhipuClient(
        response=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        content=json.dumps(
                            [
                                {
                                    "info": "某产品在 2026 年扩展企业搜索能力。",
                                    "title": "企业搜索能力发布",
                                    "link": "https://example.com/a",
                                }
                            ],
                            ensure_ascii=False,
                        ),
                        reasoning_content="已有信息足够，停止搜集。",
                    ),
                )
            ]
        )
    )
    adapter = ZhipuCollectorAgent(client=raw_client, model="glm-test")

    decision = await adapter.plan(
        CollectorInvocation(
            prompt_name="collector_round",
            subtask_id="sub_1",
            plan=CollectPlan(
                tool_call_id="call_collect_1",
                revision_id="rev_1",
                collect_target="收集主要玩家",
                additional_info="优先官方与高可信媒体。",
                freshness_requirement=FreshnessRequirement.HIGH,
            ),
            call_index=3,
            tool_call_limit=10,
            now=SimpleNamespace(isoformat=lambda: "2026-03-16T15:00:00+00:00"),
            profile=build_stage_profile(Settings(), stage="collector"),
            prompt_bundle=PromptBundle(
                system_prompt="collector-system",
                user_prompt="collector-user",
            ),
            tool_schemas=(
                build_web_search_tool_schema(),
                build_web_fetch_tool_schema(),
            ),
        )
    )

    assert decision.stop is True
    assert decision.reasoning_text == "已有信息足够，停止搜集。"
    assert decision.provider_finish_reason == "stop"
    assert decision.content_text.startswith("[")
    assert decision.tool_calls == ()
    assert [item.title for item in decision.items] == ["企业搜索能力发布"]


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
async def test_zhipu_llm_adapter_maps_stream_read_timeout_to_retryable_error() -> None:
    adapter = ZhipuClarificationGenerator(
        client=FakeZhipuClient(response=RaisingStreamResponse()),
        model="glm-test",
    )

    with pytest.raises(RetryableLLMError):
        await adapter.generate_natural(
            LLMInvocation(
                profile=build_stage_profile(Settings(), stage="clarification_natural"),
                prompt_bundle=PromptBundle(system_prompt=None, user_prompt="private prompt"),
            )
        )


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
async def test_web_search_maps_prd_recency_filter_to_provider_request_value() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["search_recency_filter"] == "oneWeek"
        return httpx.Response(
            status_code=200,
            json={
                "search_result": [
                    {
                        "title": "近一周动态",
                        "link": "https://example.com/week",
                        "content": "近一周新增企业版动态。",
                    }
                ]
            },
        )

    adapter = ZhipuWebSearchClient(
        api_key="secret-key",
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        transport=httpx.MockTransport(handler),
    )

    result = await adapter.search("中国 AI 搜索 产品 2026", "oneWeek")

    assert result.recency_filter == "oneWeek"


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


# --- Diagnostic extraction tests ---


class TestExtractResponseWithDiagnostics:
    def test_normal_response_returns_text_and_diagnostics(self) -> None:
        response = SimpleNamespace(
            id="req_123",
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20),
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content="hello world"),
                )
            ],
        )
        text, diag, tool_calls = _extract_response_with_diagnostics(response)
        assert text == "hello world"
        assert diag["type"] == "non_stream"
        assert diag["request_id"] == "req_123"
        assert diag["choices_count"] == 1
        assert diag["finish_reason"] == "stop"
        assert diag["content_type"] == "str"
        assert "hello world" in diag["content_repr"]
        assert diag["usage"] is not None
        assert tool_calls == ()

    def test_empty_content_returns_diagnostics_with_finish_reason(self) -> None:
        response = SimpleNamespace(
            id="req_456",
            usage=None,
            choices=[
                SimpleNamespace(
                    finish_reason="length",
                    message=SimpleNamespace(content=""),
                )
            ],
        )
        text, diag, _ = _extract_response_with_diagnostics(response)
        assert text == ""
        assert diag["finish_reason"] == "length"
        assert diag["content_type"] == "str"

    def test_no_choices_returns_empty_with_type_info(self) -> None:
        response = SimpleNamespace(id=None, usage=None, choices=[])
        text, diag, tool_calls = _extract_response_with_diagnostics(response)
        assert text == ""
        assert diag["choices_count"] == 0
        assert tool_calls == ()

    def test_dict_response_format(self) -> None:
        response = {
            "id": "req_dict",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": "dict content"},
                }
            ],
        }
        text, diag, _ = _extract_response_with_diagnostics(response)
        assert text == "dict content"
        assert diag["finish_reason"] == "stop"

    def test_response_with_tool_calls(self) -> None:
        response = SimpleNamespace(
            id="req_tc",
            usage=None,
            choices=[
                SimpleNamespace(
                    finish_reason="tool_calls",
                    message=SimpleNamespace(
                        content="",
                        tool_calls=[
                            SimpleNamespace(
                                id="call_1",
                                function=SimpleNamespace(
                                    name="collect_agent",
                                    arguments='{"collect_target":"目标"}',
                                ),
                            )
                        ],
                    ),
                )
            ],
        )
        text, diag, tool_calls = _extract_response_with_diagnostics(response)
        assert text == ""
        assert diag["finish_reason"] == "tool_calls"
        assert len(tool_calls) == 1
        assert tool_calls[0]["id"] == "call_1"
        assert tool_calls[0]["name"] == "collect_agent"
        assert tool_calls[0]["arguments"] == '{"collect_target":"目标"}'

    def test_response_extracts_reasoning_content_separately_from_text(self) -> None:
        response = SimpleNamespace(
            id="req_reasoning",
            usage=None,
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        content="最终正文。",
                        reasoning_content="先分析结构，再补正文。",
                    ),
                )
            ],
        )

        text, diag, tool_calls = _extract_response_with_diagnostics(response)

        assert text == "最终正文。"
        assert tool_calls == ()
        assert diag["reasoning_text"] == "先分析结构，再补正文。"


class TestExtractStreamWithDiagnostics:
    def test_normal_stream_returns_text_and_diagnostics(self) -> None:
        chunks = [
            SimpleNamespace(
                id="req_s1",
                usage=None,
                choices=[
                    SimpleNamespace(
                        finish_reason=None,
                        delta=SimpleNamespace(content="hello "),
                    )
                ],
            ),
            SimpleNamespace(
                id="req_s1",
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        delta=SimpleNamespace(content="world"),
                    )
                ],
            ),
        ]
        text, diag, tool_calls = _extract_stream_with_diagnostics(iter(chunks))
        assert text == "hello world"
        assert diag["type"] == "stream"
        assert diag["request_id"] == "req_s1"
        assert diag["chunk_count"] == 2
        assert diag["content_chunks"] == 2
        assert diag["empty_content_chunks"] == 0
        assert diag["no_choices_chunks"] == 0
        assert diag["finish_reasons"] == ["stop"]
        assert diag["usage"] is not None
        assert tool_calls == ()

    def test_empty_stream_returns_diagnostics(self) -> None:
        text, diag, tool_calls = _extract_stream_with_diagnostics(iter([]))
        assert text == ""
        assert diag["chunk_count"] == 0
        assert diag["content_chunks"] == 0
        assert diag["finish_reasons"] == []
        assert diag["request_id"] is None
        assert tool_calls == ()

    def test_stream_with_all_empty_content_chunks(self) -> None:
        chunks = [
            SimpleNamespace(
                id="req_empty",
                usage=None,
                choices=[
                    SimpleNamespace(
                        finish_reason=None,
                        delta=SimpleNamespace(content=None),
                    )
                ],
            ),
            SimpleNamespace(
                id="req_empty",
                usage=SimpleNamespace(total_tokens=100),
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        delta=SimpleNamespace(content=""),
                    )
                ],
            ),
        ]
        text, diag, _ = _extract_stream_with_diagnostics(iter(chunks))
        assert text == ""
        assert diag["chunk_count"] == 2
        assert diag["empty_content_chunks"] == 2
        assert diag["content_chunks"] == 0
        assert diag["finish_reasons"] == ["stop"]
        assert diag["last_chunk"] is not None

    def test_stream_dict_chunks(self) -> None:
        chunks = [
            {
                "id": "req_d",
                "usage": None,
                "choices": [
                    {"finish_reason": None, "delta": {"content": "part1"}},
                ],
            },
            {
                "id": "req_d",
                "usage": {"total_tokens": 50},
                "choices": [
                    {"finish_reason": "stop", "delta": {"content": "part2"}},
                ],
            },
        ]
        text, diag, _ = _extract_stream_with_diagnostics(iter(chunks))
        assert text == "part1part2"
        assert diag["request_id"] == "req_d"
        assert diag["finish_reasons"] == ["stop"]

    def test_stream_chunks_without_choices_are_counted(self) -> None:
        chunks = [
            SimpleNamespace(id="req_no", usage=None, choices=None),
            SimpleNamespace(
                id="req_no",
                usage=None,
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        delta=SimpleNamespace(content="data"),
                    )
                ],
            ),
        ]
        text, diag, _ = _extract_stream_with_diagnostics(iter(chunks))
        assert text == "data"
        assert diag["chunk_count"] == 2
        # First chunk has no choices → skipped by continue, not counted as content or empty
        assert diag["content_chunks"] == 1
        assert diag["empty_content_chunks"] == 0

    def test_stream_single_tool_call_incremental(self) -> None:
        chunks = [
            SimpleNamespace(
                id="req_tc",
                usage=None,
                choices=[
                    SimpleNamespace(
                        finish_reason=None,
                        delta=SimpleNamespace(
                            content=None,
                            tool_calls=[
                                SimpleNamespace(
                                    index=0,
                                    id="call_1",
                                    function=SimpleNamespace(
                                        name="collect_agent",
                                        arguments='{"collect_',
                                    ),
                                )
                            ],
                        ),
                    )
                ],
            ),
            SimpleNamespace(
                id="req_tc",
                usage=None,
                choices=[
                    SimpleNamespace(
                        finish_reason=None,
                        delta=SimpleNamespace(
                            content=None,
                            tool_calls=[
                                SimpleNamespace(
                                    index=0,
                                    id=None,
                                    function=SimpleNamespace(
                                        name=None,
                                        arguments='target":"目标"}',
                                    ),
                                )
                            ],
                        ),
                    )
                ],
            ),
            SimpleNamespace(
                id="req_tc",
                usage=None,
                choices=[
                    SimpleNamespace(
                        finish_reason="tool_calls",
                        delta=SimpleNamespace(content=None),
                    )
                ],
            ),
        ]
        text, diag, tool_calls = _extract_stream_with_diagnostics(iter(chunks))
        assert text == ""
        assert len(tool_calls) == 1
        assert tool_calls[0]["id"] == "call_1"
        assert tool_calls[0]["name"] == "collect_agent"
        assert tool_calls[0]["arguments"] == '{"collect_target":"目标"}'
        assert diag["finish_reasons"] == ["tool_calls"]

    def test_stream_multiple_concurrent_tool_calls(self) -> None:
        chunks = [
            SimpleNamespace(
                id="req_mc",
                usage=None,
                choices=[
                    SimpleNamespace(
                        finish_reason=None,
                        delta=SimpleNamespace(
                            content=None,
                            tool_calls=[
                                SimpleNamespace(
                                    index=0,
                                    id="call_a",
                                    function=SimpleNamespace(
                                        name="collect_agent",
                                        arguments='{"collect_target":"A","additional_info":"a","freshness_requirement":"high"}',
                                    ),
                                ),
                                SimpleNamespace(
                                    index=1,
                                    id="call_b",
                                    function=SimpleNamespace(
                                        name="collect_agent",
                                        arguments='{"collect_target":"B","additional_info":"b","freshness_requirement":"high"}',
                                    ),
                                ),
                            ],
                        ),
                    )
                ],
            ),
        ]
        text, diag, tool_calls = _extract_stream_with_diagnostics(iter(chunks))
        assert len(tool_calls) == 2
        assert tool_calls[0]["id"] == "call_a"
        assert tool_calls[1]["id"] == "call_b"

    def test_stream_extracts_reasoning_content_without_mixing_into_text(self) -> None:
        chunks = [
            SimpleNamespace(
                id="req_writer_stream",
                usage=None,
                choices=[
                    SimpleNamespace(
                        finish_reason=None,
                        delta=SimpleNamespace(
                            reasoning_content="先分析图表结构。",
                            content="第一段正文。",
                        ),
                    )
                ],
            ),
            SimpleNamespace(
                id="req_writer_stream",
                usage=None,
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        delta=SimpleNamespace(
                            reasoning_content="继续完成结论。",
                            content="第二段正文。",
                        ),
                    )
                ],
            ),
        ]

        text, diag, tool_calls = _extract_stream_with_diagnostics(iter(chunks))

        assert text == "第一段正文。第二段正文。"
        assert tool_calls == ()
        assert diag["reasoning_text"] == "先分析图表结构。继续完成结论。"


class TestSafeRepr:
    def test_none_returns_none(self) -> None:
        assert _safe_repr(None) is None

    def test_short_object(self) -> None:
        assert _safe_repr("hello") == "'hello'"

    def test_truncation(self) -> None:
        result = _safe_repr("x" * 500, max_len=50)
        assert result is not None
        assert len(result) == 53  # 50 + "..."
        assert result.endswith("...")


@pytest.mark.asyncio
async def test_zhipu_empty_text_logs_diagnostics(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When LLM returns empty text, the warning log must include diagnostics dict."""
    raw_client = FakeZhipuClient(
        response=SimpleNamespace(
            id="req_diag",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=""),
                    finish_reason="length",
                )
            ],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=0),
        )
    )
    adapter = ZhipuClarificationGenerator(client=raw_client, model="glm-test")

    with pytest.raises(RetryableLLMError):
        await adapter.generate_natural(
            LLMInvocation(
                profile=build_stage_profile(Settings(), stage="clarification_natural"),
                prompt_bundle=PromptBundle(system_prompt=None, user_prompt="test"),
            )
        )

    warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warning_records) >= 1
    msg = warning_records[0].message
    assert "diagnostics" in msg
    assert "finish_reason" in msg


@pytest.mark.asyncio
async def test_zhipu_starting_log_includes_prompt_chars(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The starting log must include prompt_chars, thinking, and stream fields."""
    raw_client = FakeZhipuClient(
        response=SimpleNamespace(
            id="req_pc",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="ok"),
                )
            ],
        )
    )
    adapter = ZhipuClarificationGenerator(client=raw_client, model="glm-test")

    await adapter.generate_natural(
        LLMInvocation(
            profile=build_stage_profile(Settings(), stage="clarification_natural"),
            prompt_bundle=PromptBundle(
                system_prompt="system msg",
                user_prompt="user msg",
            ),
        )
    )

    info_records = [r for r in caplog.records if r.levelname == "INFO"]
    starting_msg = next(r.message for r in info_records if "call starting" in r.message)
    assert "prompt_chars=" in starting_msg
    assert "thinking=" in starting_msg
    assert "stream=" in starting_msg


@pytest.mark.asyncio
async def test_zhipu_completion_propagates_non_stream_provider_finish_reason_and_usage() -> None:
    client = ZhipuChatClient(
        client=FakeZhipuClient(
            response=SimpleNamespace(
                id="req_non_stream_obs",
                usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7, total_tokens=18),
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(content="正文。"),
                    )
                ],
            )
        )
    )

    result = await client.complete(
        invocation=LLMInvocation(
            profile=build_stage_profile(Settings(), stage="clarification_natural"),
            prompt_bundle=PromptBundle(system_prompt=None, user_prompt="test"),
        )
    )

    assert isinstance(result, ZhipuCompletionResult)
    assert result.provider_finish_reason == "stop"
    assert result.provider_usage == {
        "prompt_tokens": 11,
        "completion_tokens": 7,
        "total_tokens": 18,
    }


@pytest.mark.asyncio
async def test_zhipu_completion_propagates_stream_provider_finish_reason_and_usage() -> None:
    client = ZhipuChatClient(
        client=FakeZhipuClient(
            response=iter(
                [
                    {
                        "id": "req_stream_obs",
                        "usage": None,
                        "choices": [
                            {"finish_reason": None, "delta": {"content": "第一段"}},
                        ],
                    },
                    {
                        "id": "req_stream_obs",
                        "usage": {"prompt_tokens": 20, "completion_tokens": 9, "total_tokens": 29},
                        "choices": [
                            {"finish_reason": "tool_calls", "delta": {"content": "第二段"}},
                        ],
                    },
                ]
            )
        )
    )

    result = await client.complete(
        invocation=LLMInvocation(
            profile=build_stage_profile(Settings(), stage="planner"),
            prompt_bundle=PromptBundle(system_prompt="system", user_prompt="user"),
            tool_schemas=(build_collect_agent_tool_schema(),),
        )
    )

    assert result.provider_finish_reason == "tool_calls"
    assert result.provider_usage == {
        "prompt_tokens": 20,
        "completion_tokens": 9,
        "total_tokens": 29,
    }


@pytest.mark.asyncio
async def test_complete_empty_text_with_tool_calls_does_not_raise() -> None:
    """When text is empty but tool_calls are present, complete() should not raise."""
    from app.infrastructure.llm.zhipu import ZhipuChatClient, ZhipuCompletionResult

    raw_client = FakeZhipuClient(
        response=SimpleNamespace(
            id="req_tc_ok",
            choices=[
                SimpleNamespace(
                    finish_reason="tool_calls",
                    message=SimpleNamespace(
                        content="",
                        tool_calls=[
                            SimpleNamespace(
                                id="call_1",
                                function=SimpleNamespace(
                                    name="collect_agent",
                                    arguments='{"collect_target":"X"}',
                                ),
                            )
                        ],
                    ),
                )
            ],
        )
    )
    client = ZhipuChatClient(client=raw_client)
    result = await client.complete(
        invocation=LLMInvocation(
            profile=build_stage_profile(Settings(), stage="clarification_natural"),
            prompt_bundle=PromptBundle(system_prompt=None, user_prompt="test"),
        )
    )
    assert isinstance(result, ZhipuCompletionResult)
    assert result.text == ""
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "collect_agent"


@pytest.mark.asyncio
async def test_zhipu_writer_agent_maps_provider_reasoning_to_writer_decision() -> None:
    raw_client = FakeZhipuClient(
        response=SimpleNamespace(
            id="req_writer_reasoning",
            choices=[
                SimpleNamespace(
                    finish_reason="tool_calls",
                    message=SimpleNamespace(
                        content="先给出上半段正文。",
                        reasoning_content="先总结背景，再决定画图。",
                        tool_calls=[
                            SimpleNamespace(
                                id="call_writer_1",
                                function=SimpleNamespace(
                                    name="python_interpreter",
                                    arguments='{"code":"print(1)"}',
                                ),
                            )
                        ],
                    ),
                )
            ],
        )
    )
    agent = ZhipuWriterAgent(client=ZhipuChatClient(client=raw_client), model="glm-test")

    decision = await agent.write(_build_writer_invocation())

    assert decision.text == "先给出上半段正文。"
    assert decision.reasoning_text == "先总结背景，再决定画图。"
    assert decision.provider_finish_reason == "tool_calls"
    assert len(decision.tool_calls) == 1
    assert decision.tool_calls[0].tool_call_id == "call_writer_1"


@pytest.mark.asyncio
async def test_zhipu_completed_log_includes_provider_observability_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = ZhipuChatClient(
        client=FakeZhipuClient(
            response=SimpleNamespace(
                id="req_obs_log",
                usage=SimpleNamespace(prompt_tokens=5, completion_tokens=3),
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(content="done"),
                    )
                ],
            )
        )
    )

    await client.complete(
        invocation=LLMInvocation(
            profile=build_stage_profile(Settings(), stage="clarification_natural"),
            prompt_bundle=PromptBundle(system_prompt=None, user_prompt="test"),
        )
    )

    record = next(r for r in caplog.records if "call completed" in r.message)
    assert record.request_id == "req_obs_log"
    assert record.provider_finish_reason == "stop"
    assert record.provider_usage == {
        "prompt_tokens": 5,
        "completion_tokens": 3,
    }
    assert record.response_length == 4
    assert record.tool_calls_count == 0


def _build_planner_invocation(*, call_index: int = 1) -> PlannerInvocation:
    return PlannerInvocation(
        prompt_name="planner_round",
        requirement_detail=_build_requirement_detail(),
        summaries=(),
        call_index=call_index,
        collect_agent_calls_used=0,
        now=SimpleNamespace(isoformat=lambda: "2026-03-16T15:00:00+00:00"),
        profile=build_stage_profile(Settings(), stage="planner"),
        prompt_bundle=PromptBundle(
            system_prompt="system",
            user_prompt="user",
        ),
        tool_schemas=(build_collect_agent_tool_schema(),),
    )


@pytest.mark.asyncio
async def test_planner_parses_tool_calls_response() -> None:
    raw_client = FakeZhipuClient(
        response=SimpleNamespace(
            id="req_plan_tc",
            choices=[
                SimpleNamespace(
                    finish_reason="tool_calls",
                    message=SimpleNamespace(
                        content="",
                        tool_calls=[
                            SimpleNamespace(
                                id="call_tc_1",
                                function=SimpleNamespace(
                                    name="collect_agent",
                                    arguments=json.dumps({
                                        "collect_target": "中国 AI 市场",
                                        "additional_info": "聚焦 2025 年",
                                        "freshness_requirement": "high",
                                    }, ensure_ascii=False),
                                ),
                            ),
                            SimpleNamespace(
                                id="call_tc_2",
                                function=SimpleNamespace(
                                    name="collect_agent",
                                    arguments=json.dumps({
                                        "collect_target": "竞品分析",
                                        "additional_info": "对比主要竞争者",
                                    }, ensure_ascii=False),
                                ),
                            ),
                        ],
                    ),
                )
            ],
        )
    )
    adapter = ZhipuPlannerAgent(client=raw_client, model="glm-test")
    decision = await adapter.plan(_build_planner_invocation())

    assert decision.stop is False
    assert decision.provider_finish_reason == "tool_calls"
    assert len(decision.plans) == 2
    assert decision.plans[0].tool_call_id == "call_tc_1"
    assert decision.plans[0].collect_target == "中国 AI 市场"
    assert decision.plans[0].freshness_requirement == FreshnessRequirement.HIGH
    assert decision.plans[1].tool_call_id == "call_tc_2"
    assert decision.plans[1].collect_target == "竞品分析"
    assert decision.plans[1].freshness_requirement == FreshnessRequirement.HIGH


@pytest.mark.asyncio
async def test_planner_parses_content_json_response() -> None:
    raw_client = FakeZhipuClient(
        response=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps({
                            "reasoning_deltas": ["先补公开资料"],
                            "stop": False,
                            "plans": [
                                {
                                    "collect_target": "目标 A",
                                    "additional_info": "补充 A",
                                    "freshness_requirement": "high",
                                }
                            ],
                        }, ensure_ascii=False)
                    )
                )
            ]
        )
    )
    adapter = ZhipuPlannerAgent(client=raw_client, model="glm-test")
    decision = await adapter.plan(_build_planner_invocation())

    assert decision.stop is False
    assert decision.provider_finish_reason is None
    assert len(decision.plans) == 1
    assert decision.plans[0].collect_target == "目标 A"
    assert decision.reasoning_deltas == ("先补公开资料",)


@pytest.mark.asyncio
async def test_planner_natural_language_text_returns_stop_true() -> None:
    raw_client = FakeZhipuClient(
        response=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="已经完成了所有信息收集，无需继续。"
                    )
                )
            ]
        )
    )
    adapter = ZhipuPlannerAgent(client=raw_client, model="glm-test")
    decision = await adapter.plan(_build_planner_invocation())

    assert decision.stop is True
    assert decision.plans == ()


@pytest.mark.asyncio
async def test_planner_skips_non_collect_agent_tool_calls() -> None:
    raw_client = FakeZhipuClient(
        response=SimpleNamespace(
            id="req_skip",
            choices=[
                SimpleNamespace(
                    finish_reason="tool_calls",
                    message=SimpleNamespace(
                        content="",
                        tool_calls=[
                            SimpleNamespace(
                                id="call_other",
                                function=SimpleNamespace(
                                    name="some_other_tool",
                                    arguments='{"key":"value"}',
                                ),
                            ),
                            SimpleNamespace(
                                id="call_valid",
                                function=SimpleNamespace(
                                    name="collect_agent",
                                    arguments=json.dumps({
                                        "collect_target": "有效目标",
                                        "additional_info": "补充",
                                    }, ensure_ascii=False),
                                ),
                            ),
                        ],
                    ),
                )
            ],
        )
    )
    adapter = ZhipuPlannerAgent(client=raw_client, model="glm-test")
    decision = await adapter.plan(_build_planner_invocation())

    assert len(decision.plans) == 1
    assert decision.plans[0].collect_target == "有效目标"
    assert decision.plans[0].tool_call_id == "call_valid"
