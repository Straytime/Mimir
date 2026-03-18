from datetime import UTC, datetime

from app.application.dto.research import (
    CollectorInvocation,
    PlannerInvocation,
    SummaryInvocation,
)
from app.application.prompts.collection import (
    build_collector_prompt,
    build_planner_prompt,
    build_summary_prompt,
)
from app.domain.enums import FreshnessRequirement, OutputFormat
from app.domain.schemas import CollectPlan, CollectSummary, RequirementDetail


NOW = datetime(2026, 3, 16, 15, 0, tzinfo=UTC)


def build_requirement_detail() -> RequirementDetail:
    return RequirementDetail(
        research_goal="分析中国 AI 搜索产品的竞争格局与机会",
        domain="互联网 / AI 产品",
        requirement_details="聚焦中国市场，偏商业分析，覆盖近两年变化。",
        output_format=OutputFormat.BUSINESS_REPORT,
        freshness_requirement=FreshnessRequirement.HIGH,
        language="zh-CN",
    )


def build_collect_plan(index: int = 1) -> CollectPlan:
    return CollectPlan(
        tool_call_id=f"call_{index}",
        revision_id="rev_001",
        collect_target=f"收集目标 {index}",
        additional_info="优先官方发布与高可信媒体。",
        freshness_requirement=FreshnessRequirement.HIGH,
    )


def test_planner_prompt_semantic_lock_keeps_role_limits_and_transcript_order() -> None:
    prompt = build_planner_prompt(
        invocation=PlannerInvocation(
            prompt_name="planner_round",
            requirement_detail=build_requirement_detail(),
            summaries=(
                CollectSummary(
                    tool_call_id="call_1",
                    subtask_id="sub_1",
                    collect_target="收集目标 1",
                    status="completed",
                    search_queries=["中国 AI 搜索 产品 2025"],
                    key_findings_markdown="- 已出现多个垂直场景产品。",
                ),
                CollectSummary(
                    tool_call_id="call_2",
                    subtask_id="sub_2",
                    collect_target="收集目标 2",
                    status="completed",
                    search_queries=["中国 AI 搜索 商业化 2025"],
                    key_findings_markdown="- B 端落地开始加速。",
                ),
            ),
            call_index=2,
            collect_agent_calls_used=3,
            now=NOW,
        )
    )

    assert "信息搜集调度 agent" in prompt.system_prompt
    assert "最多同时发起 3 个工具调用" in prompt.system_prompt
    assert "collect_agent" in prompt.system_prompt
    assert "2026-03-16T15:00:00+00:00" in prompt.user_prompt
    assert "分析中国 AI 搜索产品的竞争格局与机会" in prompt.user_prompt
    assert "当前 collect_agent 已使用次数: 3" in prompt.user_prompt
    assert [message.role for message in prompt.transcript] == ["assistant", "tool", "tool"]
    assistant_msg = prompt.transcript[0]
    assert assistant_msg.tool_calls is not None
    assert len(assistant_msg.tool_calls) == 2
    assert [tc["id"] for tc in assistant_msg.tool_calls] == ["call_1", "call_2"]
    tool_msgs = [m for m in prompt.transcript if m.role == "tool"]
    assert [m.tool_call_id for m in tool_msgs] == ["call_1", "call_2"]
    assert "收集目标 1" in tool_msgs[0].content
    assert "收集目标 2" in tool_msgs[1].content


def test_collector_prompt_semantic_lock_keeps_tool_range_and_limits() -> None:
    prompt = build_collector_prompt(
        invocation=CollectorInvocation(
            prompt_name="collector_round",
            subtask_id="sub_1",
            plan=build_collect_plan(),
            call_index=1,
            tool_call_limit=10,
            now=NOW,
        )
    )

    assert "你是一个信息搜集 agent" in prompt.system_prompt
    assert "max_tool_calls = 10" in prompt.system_prompt
    assert "web_search" in prompt.system_prompt
    assert "web_fetch" in prompt.system_prompt
    assert "高质量的关键信息和数据" in prompt.system_prompt
    assert "<信息获取目标>" in prompt.user_prompt
    assert "收集目标 1" in prompt.user_prompt
    assert "优先官方发布与高可信媒体。" in prompt.user_prompt
    assert "high" in prompt.user_prompt


def test_summary_prompt_semantic_lock_keeps_schema_and_runtime_inputs() -> None:
    prompt = build_summary_prompt(
        invocation=SummaryInvocation(
            prompt_name="summary_round",
            subtask_id="sub_1",
            plan=build_collect_plan(),
            result_status="completed",
            search_queries=("中国 AI 搜索 产品 2025",),
            item_payloads=(
                {
                    "title": "某公司发布会回顾",
                    "link": "https://example.com/article",
                    "info": "某产品在 2025 年发布企业版能力。",
                },
            ),
            now=NOW,
        )
    )

    assert "关键信息总结助手" in prompt.system_prompt
    assert "提取5-10条关键发现" in prompt.system_prompt
    assert "markdown 格式直接输出" in prompt.system_prompt
    assert "<信息获取目标>" in prompt.user_prompt
    assert "收集目标 1" in prompt.user_prompt
    assert "中国 AI 搜索 产品 2025" in prompt.user_prompt
    assert "某公司发布会回顾" in prompt.user_prompt
    assert "completed" in prompt.user_prompt
