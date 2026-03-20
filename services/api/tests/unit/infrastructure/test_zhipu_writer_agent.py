"""Unit tests for ZhipuWriterAgent API tool_calls parsing."""
import json
from datetime import UTC, datetime

import pytest

from app.application.dto.delivery import WriterInvocation, ResearchOutline, OutlineSection
from app.application.dto.invocation import InvocationProfile, PromptBundle, ToolSchema
from app.application.dto.research import FormattedSource
from app.domain.enums import FreshnessRequirement, OutputFormat
from app.domain.schemas import RequirementDetail
from app.infrastructure.delivery.zhipu import ZhipuWriterAgent
from app.infrastructure.llm.zhipu import ZhipuChatClient, ZhipuCompletionResult

NOW = datetime(2026, 3, 19, 10, 0, tzinfo=UTC)


def _requirement() -> RequirementDetail:
    return RequirementDetail(
        research_goal="\u5206\u6790\u4e2d\u56fd AI \u641c\u7d22\u4ea7\u54c1\u7684\u7ade\u4e89\u683c\u5c40",
        domain="\u4e92\u8054\u7f51 / AI \u4ea7\u54c1",
        requirement_details="\u805a\u7126\u4e2d\u56fd\u5e02\u573a\u3002",
        output_format=OutputFormat.BUSINESS_REPORT,
        freshness_requirement=FreshnessRequirement.HIGH,
        language="zh-CN",
    )


def _outline() -> ResearchOutline:
    return ResearchOutline(
        title="\u4e2d\u56fd AI \u641c\u7d22\u7ade\u4e89\u683c\u5c40\u7814\u7a76",
        sections=(
            OutlineSection(
                section_id="section_1",
                title="\u7814\u7a76\u80cc\u666f",
                description="\u5206\u6790\u5e02\u573a\u80cc\u666f\u4e0e\u7814\u7a76\u8303\u56f4\u3002",
                order=1,
            ),
        ),
        entities=("AI \u641c\u7d22\u4ea7\u54c1",),
    )


def _invocation(*, prompt_bundle: PromptBundle | None = None) -> WriterInvocation:
    return WriterInvocation(
        prompt_name="writer_round",
        requirement_detail=_requirement(),
        formatted_sources=(
            FormattedSource(
                refer="ref_1",
                title="\u6d4b\u8bd5\u6765\u6e90",
                link="https://example.com/1",
                info="\u6d4b\u8bd5\u4fe1\u606f",
            ),
        ),
        outline=_outline(),
        now=NOW,
        profile=InvocationProfile(
            stage="writer",
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
        tool_schemas=(
            ToolSchema(
                name="python_interpreter",
                description="Execute Python code",
                parameters={"code": {"type": "string", "description": "Python code"}},
                required=("code",),
            ),
        ),
    )


class FakeZhipuChatClient(ZhipuChatClient):
    """Returns a ZhipuCompletionResult with configurable text and tool_calls."""

    def __init__(self, text: str, tool_calls: tuple[dict, ...] = ()) -> None:
        self._text = text
        self._tool_calls = tool_calls
        self.calls: list[dict] = []

    async def complete(self, *, invocation):
        self.calls.append({"invocation": invocation})
        return ZhipuCompletionResult(
            text=self._text,
            request_id="req_test",
            tool_calls=self._tool_calls,
        )


@pytest.mark.asyncio
async def test_writer_returns_text_directly() -> None:
    """WriterDecision.text is the direct LLM text output."""
    client = FakeZhipuChatClient(
        text="# \u7814\u7a76\u62a5\u544a\n\n\u6b63\u6587\u5185\u5bb9\u3002",
    )
    agent = ZhipuWriterAgent(client=client, model="glm-5")
    decision = await agent.write(_invocation())

    assert decision.text == "# \u7814\u7a76\u62a5\u544a\n\n\u6b63\u6587\u5185\u5bb9\u3002"
    assert decision.tool_calls == ()


@pytest.mark.asyncio
async def test_writer_parses_api_tool_calls() -> None:
    """WriterDecision.tool_calls are parsed from API tool_calls."""
    tool_calls = (
        {
            "id": "call_1",
            "name": "python_interpreter",
            "arguments": json.dumps({"code": "print('hello')"}),
        },
    )
    client = FakeZhipuChatClient(
        text="\u7ed8\u5236\u56fe\u8868\u540e\u7ee7\u7eed\u3002",
        tool_calls=tool_calls,
    )
    agent = ZhipuWriterAgent(client=client, model="glm-5")
    decision = await agent.write(_invocation())

    assert len(decision.tool_calls) == 1
    assert decision.tool_calls[0].tool_call_id == "call_1"
    assert decision.tool_calls[0].tool_name == "python_interpreter"
    assert decision.tool_calls[0].code == "print('hello')"
    assert decision.text == "\u7ed8\u5236\u56fe\u8868\u540e\u7ee7\u7eed\u3002"


@pytest.mark.asyncio
async def test_writer_skips_non_python_interpreter_tool_calls() -> None:
    """Only python_interpreter tool calls are included."""
    tool_calls = (
        {
            "id": "call_1",
            "name": "web_search",
            "arguments": json.dumps({"query": "test"}),
        },
        {
            "id": "call_2",
            "name": "python_interpreter",
            "arguments": json.dumps({"code": "1+1"}),
        },
    )
    client = FakeZhipuChatClient(text="text", tool_calls=tool_calls)
    agent = ZhipuWriterAgent(client=client, model="glm-5")
    decision = await agent.write(_invocation())

    assert len(decision.tool_calls) == 1
    assert decision.tool_calls[0].tool_call_id == "call_2"


@pytest.mark.asyncio
async def test_writer_skips_empty_code_tool_calls() -> None:
    """Tool calls with empty code are skipped."""
    tool_calls = (
        {
            "id": "call_1",
            "name": "python_interpreter",
            "arguments": json.dumps({"code": ""}),
        },
        {
            "id": "call_2",
            "name": "python_interpreter",
            "arguments": json.dumps({"code": "  "}),
        },
    )
    client = FakeZhipuChatClient(text="text", tool_calls=tool_calls)
    agent = ZhipuWriterAgent(client=client, model="glm-5")
    decision = await agent.write(_invocation())

    assert len(decision.tool_calls) == 0


@pytest.mark.asyncio
async def test_writer_assigns_fallback_tool_call_id() -> None:
    """When tool call has no id, a fallback id is generated."""
    tool_calls = (
        {
            "name": "python_interpreter",
            "arguments": json.dumps({"code": "x = 1"}),
        },
    )
    client = FakeZhipuChatClient(text="text", tool_calls=tool_calls)
    agent = ZhipuWriterAgent(client=client, model="glm-5")
    decision = await agent.write(_invocation())

    assert len(decision.tool_calls) == 1
    assert decision.tool_calls[0].tool_call_id == "writer_tool_1"


@pytest.mark.asyncio
async def test_writer_skips_malformed_arguments_json() -> None:
    """Tool calls with invalid JSON arguments are skipped."""
    tool_calls = (
        {
            "id": "call_1",
            "name": "python_interpreter",
            "arguments": "not valid json",
        },
    )
    client = FakeZhipuChatClient(text="text", tool_calls=tool_calls)
    agent = ZhipuWriterAgent(client=client, model="glm-5")
    decision = await agent.write(_invocation())

    assert len(decision.tool_calls) == 0


@pytest.mark.asyncio
async def test_writer_strips_text_whitespace() -> None:
    """WriterDecision.text has leading/trailing whitespace stripped."""
    client = FakeZhipuChatClient(text="  \n hello \n  ")
    agent = ZhipuWriterAgent(client=client, model="glm-5")
    decision = await agent.write(_invocation())

    assert decision.text == "hello"


@pytest.mark.asyncio
async def test_writer_raises_on_incomplete_invocation() -> None:
    """Missing prompt_bundle or profile raises RetryableOperationError."""
    from app.application.services.invocation import RetryableOperationError

    client = FakeZhipuChatClient(text="text")
    agent = ZhipuWriterAgent(client=client, model="glm-5")
    inv = WriterInvocation(
        prompt_name="writer_round",
        requirement_detail=_requirement(),
        formatted_sources=(),
        outline=_outline(),
        now=NOW,
    )
    with pytest.raises(RetryableOperationError):
        await agent.write(inv)
