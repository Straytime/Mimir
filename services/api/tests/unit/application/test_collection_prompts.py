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


def test_planner_prompt_invariants_cover_required_fields_and_constraints() -> None:
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
            ),
            call_index=2,
            collect_agent_calls_used=3,
            now=NOW,
        )
    )

    assert "分析中国 AI 搜索产品的竞争格局与机会" in prompt
    assert "收集目标 1" in prompt
    assert "2026-03-16T15:00:00+00:00" in prompt
    assert "单轮最多 3 个 CollectPlan" in prompt
    assert "单个 Revision 累计最多 5 次 collect_agent" in prompt
    assert "只输出 stop 或 CollectPlan[]" in prompt


def test_collector_prompt_invariants_cover_required_fields_and_constraints() -> None:
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

    assert "收集目标 1" in prompt
    assert "优先官方发布与高可信媒体。" in prompt
    assert "2026-03-16T15:00:00+00:00" in prompt
    assert "最多 10 次工具调用" in prompt
    assert "web_search" in prompt
    assert "web_fetch" in prompt
    assert "search_recency_filter 使用 noLimit" in prompt


def test_summary_prompt_invariants_cover_required_fields_and_constraints() -> None:
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

    assert "收集目标 1" in prompt
    assert "某公司发布会回顾" in prompt
    assert "2026-03-16T15:00:00+00:00" in prompt
    assert "CollectSummary" in prompt
    assert "risk_blocked" in prompt
    assert "只输出压缩摘要正文" in prompt
