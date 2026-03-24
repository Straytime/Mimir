"""Unit tests for ZhipuOutlineAgent PRD key-value format parsing."""
import json
from types import SimpleNamespace

import pytest

from app.application.dto.delivery import OutlineInvocation
from app.application.dto.invocation import InvocationProfile, PromptBundle
from app.application.services.invocation import TraceableOperationError
from app.application.dto.research import FormattedSource
from app.domain.enums import FreshnessRequirement, OutputFormat
from app.domain.schemas import RequirementDetail
from app.infrastructure.delivery.zhipu import ZhipuOutlineAgent
from app.infrastructure.llm.zhipu import ZhipuChatClient, ZhipuCompletionResult

from datetime import UTC, datetime

NOW = datetime(2026, 3, 19, 10, 0, tzinfo=UTC)


def _requirement() -> RequirementDetail:
    return RequirementDetail(
        research_goal="分析中国 AI 搜索产品的竞争格局",
        domain="互联网 / AI 产品",
        requirement_details="聚焦中国市场。",
        output_format=OutputFormat.BUSINESS_REPORT,
        freshness_requirement=FreshnessRequirement.HIGH,
        language="zh-CN",
    )


def _invocation(*, prompt_bundle: PromptBundle | None = None) -> OutlineInvocation:
    return OutlineInvocation(
        prompt_name="outline_round",
        requirement_detail=_requirement(),
        formatted_sources=(
            FormattedSource(
                refer="ref_1",
                title="测试来源",
                link="https://example.com/1",
                info="测试信息",
            ),
        ),
        now=NOW,
        profile=InvocationProfile(
            stage="outline",
            model="glm-5",
            temperature=1.0,
            top_p=1.0,
            max_tokens=98304,
            thinking=True,
            clear_thinking=False,
            stream=True,
        ),
        prompt_bundle=prompt_bundle or PromptBundle(
            system_prompt="test system",
            user_prompt="test user",
        ),
    )


class FakeZhipuChatClient(ZhipuChatClient):
    """Returns a ZhipuCompletionResult with configurable text."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.calls: list[dict] = []

    async def complete(self, *, invocation):
        self.calls.append({"invocation": invocation})
        return ZhipuCompletionResult(
            text=self._text,
            request_id="req_test",
            tool_calls=(),
            request_payload=invocation.to_provider_payload(),
            response_payload={
                "request_id": "req_test",
                "parsed_text": self._text,
            },
        )


@pytest.mark.asyncio
async def test_parse_prd_key_value_format() -> None:
    """ZhipuOutlineAgent parses PRD key-value format correctly."""
    prd_response = json.dumps(
        {
            "research_outline": {
                "标题": {"title": "中国 AI 搜索竞争格局研究"},
                "section_1": {
                    "title": "研究背景",
                    "description": "分析市场背景与研究范围。",
                },
                "section_2": {
                    "title": "竞争格局",
                    "description": "评估主要竞争者的差异化能力。",
                },
                "参考来源": {
                    "title": "参考来源",
                    "description": "列明所有参考来源",
                },
            },
            "entities": ["AI 搜索产品", "中国市场"],
        },
        ensure_ascii=False,
    )
    client = FakeZhipuChatClient(prd_response)
    agent = ZhipuOutlineAgent(client=client, model="glm-5")
    decision = await agent.prepare(_invocation())

    assert decision.outline.title == "中国 AI 搜索竞争格局研究"
    assert len(decision.outline.sections) == 3
    assert decision.outline.sections[0].title == "研究背景"
    assert decision.outline.sections[0].description == "分析市场背景与研究范围。"
    assert decision.outline.sections[0].order == 1
    assert decision.outline.sections[1].title == "竞争格局"
    assert decision.outline.sections[1].order == 2
    assert decision.outline.sections[2].title == "参考来源"
    assert decision.outline.sections[2].description == "列明所有参考来源"
    assert decision.outline.sections[2].order == 3
    assert decision.outline.entities == ("AI 搜索产品", "中国市场")
    assert decision.deltas == ()


@pytest.mark.asyncio
async def test_parse_prd_format_skips_title_key_in_sections() -> None:
    """The '标题' key is used for the outline title, not as a section."""
    prd_response = json.dumps(
        {
            "research_outline": {
                "标题": {"title": "报告标题"},
                "section_1": {
                    "title": "唯一章节",
                    "description": "描述内容。",
                },
            },
            "entities": [],
        },
        ensure_ascii=False,
    )
    client = FakeZhipuChatClient(prd_response)
    agent = ZhipuOutlineAgent(client=client, model="glm-5")
    decision = await agent.prepare(_invocation())

    assert decision.outline.title == "报告标题"
    assert len(decision.outline.sections) == 1
    assert decision.outline.sections[0].title == "唯一章节"


@pytest.mark.asyncio
async def test_parse_prd_format_entities_at_top_level() -> None:
    """entities is at top level, not inside research_outline."""
    prd_response = json.dumps(
        {
            "research_outline": {
                "标题": {"title": "标题"},
                "section_1": {"title": "节", "description": "描述"},
            },
            "entities": ["实体A", "实体B", "实体C"],
        },
        ensure_ascii=False,
    )
    client = FakeZhipuChatClient(prd_response)
    agent = ZhipuOutlineAgent(client=client, model="glm-5")
    decision = await agent.prepare(_invocation())

    assert decision.outline.entities == ("实体A", "实体B", "实体C")


@pytest.mark.asyncio
async def test_parse_prd_format_missing_research_outline_raises() -> None:
    """Missing research_outline key raises TraceableOperationError with trace payload."""
    prd_response = json.dumps({"entities": []}, ensure_ascii=False)
    client = FakeZhipuChatClient(prd_response)
    agent = ZhipuOutlineAgent(client=client, model="glm-5")
    with pytest.raises(TraceableOperationError) as exc_info:
        await agent.prepare(_invocation())
    assert exc_info.value.trace_snapshot.parsed_text == prd_response
    assert exc_info.value.trace_snapshot.request_payload is not None


@pytest.mark.asyncio
async def test_parse_prd_format_no_sections_raises() -> None:
    """research_outline with only 标题 and no section keys raises traceable error."""
    prd_response = json.dumps(
        {
            "research_outline": {"标题": {"title": "标题"}},
            "entities": [],
        },
        ensure_ascii=False,
    )
    client = FakeZhipuChatClient(prd_response)
    agent = ZhipuOutlineAgent(client=client, model="glm-5")
    with pytest.raises(TraceableOperationError) as exc_info:
        await agent.prepare(_invocation())
    assert exc_info.value.trace_snapshot.parsed_text == prd_response


@pytest.mark.asyncio
async def test_outline_agent_does_not_append_json_instruction() -> None:
    """ZhipuOutlineAgent should NOT append _json_instruction to user_prompt."""
    prd_response = json.dumps(
        {
            "research_outline": {
                "标题": {"title": "标题"},
                "section_1": {"title": "节", "description": "描述"},
            },
            "entities": [],
        },
        ensure_ascii=False,
    )
    client = FakeZhipuChatClient(prd_response)
    agent = ZhipuOutlineAgent(client=client, model="glm-5")
    await agent.prepare(_invocation())

    call = client.calls[0]
    invocation = call["invocation"]
    user_prompt = invocation.prompt_bundle.user_prompt
    assert "请输出合法 JSON" not in user_prompt


@pytest.mark.asyncio
async def test_parse_prd_format_with_markdown_fence() -> None:
    """Response wrapped in markdown code fence is still parsed."""
    prd_response = "```json\n" + json.dumps(
        {
            "research_outline": {
                "标题": {"title": "标题"},
                "section_1": {"title": "节", "description": "描述"},
            },
            "entities": ["实体"],
        },
        ensure_ascii=False,
    ) + "\n```"
    client = FakeZhipuChatClient(prd_response)
    agent = ZhipuOutlineAgent(client=client, model="glm-5")
    decision = await agent.prepare(_invocation())
    assert decision.outline.title == "标题"
    assert decision.outline.entities == ("实体",)


@pytest.mark.asyncio
async def test_parse_prd_format_with_explanatory_text_around_json() -> None:
    prd_response = (
        "下面是整理后的大纲：\n"
        + json.dumps(
            {
                "research_outline": {
                    "标题": {"title": "标题"},
                    "section_1": {"title": "节", "description": "描述"},
                },
                "entities": ["实体"],
            },
            ensure_ascii=False,
        )
        + "\n请进入下一步。"
    )
    client = FakeZhipuChatClient(prd_response)
    agent = ZhipuOutlineAgent(client=client, model="glm-5")

    decision = await agent.prepare(_invocation())

    assert decision.outline.title == "标题"
    assert decision.outline.entities == ("实体",)
