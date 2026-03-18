import pytest
from datetime import UTC, datetime

from app.application.dto.research import PlannerInvocation
from app.domain.enums import FreshnessRequirement, OutputFormat
from app.domain.schemas import RequirementDetail
from app.infrastructure.research.local_stub import LocalStubPlannerAgent


NOW = datetime(2026, 3, 19, 10, 0, tzinfo=UTC)


def _requirement() -> RequirementDetail:
    return RequirementDetail(
        research_goal="分析中国 AI 搜索产品",
        domain="互联网",
        requirement_details="聚焦中国市场。",
        output_format=OutputFormat.BUSINESS_REPORT,
        freshness_requirement=FreshnessRequirement.HIGH,
        language="zh-CN",
    )


@pytest.mark.asyncio
async def test_stub_planner_first_call_empty_summaries() -> None:
    """call_index=1 with empty summaries must not raise and must return plans."""
    agent = LocalStubPlannerAgent()
    decision = await agent.plan(
        PlannerInvocation(
            prompt_name="planner_round",
            requirement_detail=_requirement(),
            summaries=(),
            call_index=1,
            collect_agent_calls_used=0,
            now=NOW,
        )
    )
    assert decision.stop is False
    assert len(decision.plans) > 0


@pytest.mark.asyncio
async def test_stub_planner_second_call_returns_stop() -> None:
    """call_index=2 must return stop=True."""
    agent = LocalStubPlannerAgent()
    decision = await agent.plan(
        PlannerInvocation(
            prompt_name="planner_round",
            requirement_detail=_requirement(),
            summaries=(),
            call_index=2,
            collect_agent_calls_used=1,
            now=NOW,
        )
    )
    assert decision.stop is True
    assert len(decision.plans) == 0
