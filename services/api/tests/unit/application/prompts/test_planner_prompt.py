from datetime import UTC, datetime

from app.application.dto.research import PlannerInvocation
from app.application.prompts.collection import build_planner_prompt
from app.domain.enums import CollectSummaryStatus, FreshnessRequirement, OutputFormat
from app.domain.schemas import CollectSummary, RequirementDetail


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


def _summary(tool_call_id: str, subtask_id: str) -> CollectSummary:
    return CollectSummary(
        tool_call_id=tool_call_id,
        subtask_id=subtask_id,
        collect_target=f"目标 {subtask_id}",
        status=CollectSummaryStatus.COMPLETED,
        search_queries=["query"],
        key_findings_markdown="- finding",
    )


def test_planner_prompt_no_summaries_has_no_tool_messages() -> None:
    """When summaries is empty, messages should only be [system, user]."""
    bundle = build_planner_prompt(
        invocation=PlannerInvocation(
            prompt_name="planner_round",
            requirement_detail=_requirement(),
            summaries=(),
            call_index=1,
            collect_agent_calls_used=0,
            now=NOW,
        )
    )
    messages = bundle.messages
    roles = [m.role for m in messages]
    assert roles == ["system", "user"]


def test_planner_prompt_with_summaries_inserts_assistant_before_tools() -> None:
    """When summaries is non-empty, an assistant message with tool_calls
    must appear before the tool messages."""
    summaries = (
        _summary("call_1", "sub_1"),
        _summary("call_2", "sub_2"),
    )
    bundle = build_planner_prompt(
        invocation=PlannerInvocation(
            prompt_name="planner_round",
            requirement_detail=_requirement(),
            summaries=summaries,
            call_index=2,
            collect_agent_calls_used=2,
            now=NOW,
        )
    )
    messages = bundle.messages
    roles = [m.role for m in messages]
    # Expected: [system, user, assistant, tool, tool]
    assert roles == ["system", "user", "assistant", "tool", "tool"]

    assistant_msg = messages[2]
    assert assistant_msg.tool_calls is not None
    assert len(assistant_msg.tool_calls) == 2
    assert assistant_msg.content == ""


def test_planner_prompt_tool_call_ids_match() -> None:
    """The assistant message's tool_calls[i].id must match
    the subsequent tool message's tool_call_id."""
    summaries = (
        _summary("call_a", "sub_a"),
        _summary("call_b", "sub_b"),
    )
    bundle = build_planner_prompt(
        invocation=PlannerInvocation(
            prompt_name="planner_round",
            requirement_detail=_requirement(),
            summaries=summaries,
            call_index=2,
            collect_agent_calls_used=2,
            now=NOW,
        )
    )
    messages = bundle.messages
    assistant_msg = messages[2]
    tool_msgs = [m for m in messages if m.role == "tool"]

    assert len(assistant_msg.tool_calls) == len(tool_msgs)
    for tc, tm in zip(assistant_msg.tool_calls, tool_msgs):
        assert tc["id"] == tm.tool_call_id
        assert tc["type"] == "function"
        assert tc["function"]["name"] == "collect_agent"
