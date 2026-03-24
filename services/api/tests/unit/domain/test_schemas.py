from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.domain.enums import (
    AccessTokenResourceType,
    AvailableAction,
    ClarificationMode,
    CollectSummaryStatus,
    FreshnessRequirement,
    OutputFormat,
    RevisionStatus,
    TaskPhase,
    TaskStatus,
)
from app.domain.schemas import (
    CollectPlan,
    CollectSummary,
    EventEnvelope,
    RequirementDetail,
    RevisionSummary,
    TaskSnapshot,
)
from app.domain.tokens import AccessTokenPayload, TaskTokenPayload


NOW = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)


def test_task_snapshot_schema_matches_stage_one_contract() -> None:
    snapshot = TaskSnapshot(
        task_id="tsk_01JABC",
        status=TaskStatus.RUNNING,
        phase=TaskPhase.CLARIFYING,
        active_revision_id="rev_01JABC",
        active_revision_number=1,
        clarification_mode=ClarificationMode.NATURAL,
        created_at=NOW,
        updated_at=NOW,
        expires_at=None,
        available_actions=[AvailableAction.SUBMIT_CLARIFICATION],
    )

    assert snapshot.model_dump(mode="json") == {
        "task_id": "tsk_01JABC",
        "status": "running",
        "phase": "clarifying",
        "active_revision_id": "rev_01JABC",
        "active_revision_number": 1,
        "clarification_mode": "natural",
        "created_at": "2026-03-15T12:00:00Z",
        "updated_at": "2026-03-15T12:00:00Z",
        "expires_at": None,
        "available_actions": ["submit_clarification"],
    }


def test_revision_summary_schema_allows_nullable_requirement_detail() -> None:
    summary = RevisionSummary(
        revision_id="rev_01JABC",
        revision_number=1,
        revision_status=RevisionStatus.IN_PROGRESS,
        started_at=NOW,
        finished_at=None,
        requirement_detail=None,
    )

    assert summary.model_dump(mode="json") == {
        "revision_id": "rev_01JABC",
        "revision_number": 1,
        "revision_status": "in_progress",
        "started_at": "2026-03-15T12:00:00Z",
        "finished_at": None,
        "requirement_detail": None,
    }


def test_requirement_detail_supports_openapi_shape_and_internal_raw_llm_output() -> None:
    detail = RequirementDetail(
        research_goal="分析中国 AI 搜索产品的竞争格局与机会",
        domain="互联网 / AI 产品",
        requirement_details="偏商业报告，关注中国市场，重点覆盖近两年变化，输出语言为中文。",
        output_format=OutputFormat.BUSINESS_REPORT,
        freshness_requirement=FreshnessRequirement.HIGH,
        language="zh-CN",
    )

    assert detail.model_dump(mode="json", exclude_none=True) == {
        "research_goal": "分析中国 AI 搜索产品的竞争格局与机会",
        "domain": "互联网 / AI 产品",
        "requirement_details": "偏商业报告，关注中国市场，重点覆盖近两年变化，输出语言为中文。",
        "output_format": "business_report",
        "freshness_requirement": "high",
        "language": "zh-CN",
    }

    enriched = detail.model_copy(
        update={
            "raw_llm_output": {
                "研究目标": "分析中国 AI 搜索产品的竞争格局与机会",
            }
        }
    )

    assert enriched.raw_llm_output == {"研究目标": "分析中国 AI 搜索产品的竞争格局与机会"}


def test_collect_plan_schema_matches_master_to_subtask_contract() -> None:
    plan = CollectPlan(
        tool_call_id="call_01JABC",
        revision_id="rev_01JABC",
        collect_target="收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
        additional_info="优先官方发布与主流媒体，中文输出。",
        freshness_requirement=FreshnessRequirement.HIGH,
    )

    assert plan.model_dump(mode="json") == {
        "tool_call_id": "call_01JABC",
        "revision_id": "rev_01JABC",
        "collect_target": "收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
        "additional_info": "优先官方发布与主流媒体，中文输出。",
        "freshness_requirement": "high",
    }


def test_collect_plan_allows_empty_additional_info_for_optional_tool_field() -> None:
    plan = CollectPlan(
        tool_call_id="call_01JABC",
        revision_id="rev_01JABC",
        collect_target="收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
        additional_info="",
        freshness_requirement=FreshnessRequirement.HIGH,
    )

    assert plan.additional_info == ""


def test_collect_summary_supports_completed_and_risk_blocked_shapes() -> None:
    summary = CollectSummary(
        tool_call_id="call_01JABC",
        subtask_id="sub_01JABC",
        collect_target="收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
        status=CollectSummaryStatus.COMPLETED,
        search_queries=["中国 AI 搜索 产品 2025"],
        key_findings_markdown="- 已有多家产品进入垂直场景。",
    )

    assert summary.model_dump(mode="json", exclude_none=True) == {
        "tool_call_id": "call_01JABC",
        "subtask_id": "sub_01JABC",
        "collect_target": "收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
        "status": "completed",
        "search_queries": ["中国 AI 搜索 产品 2025"],
        "key_findings_markdown": "- 已有多家产品进入垂直场景。",
    }

    blocked = CollectSummary(
        tool_call_id="call_01JXYZ",
        subtask_id="sub_01JXYZ",
        status=CollectSummaryStatus.RISK_BLOCKED,
        message="触发风控敏感，请重新规划",
    )

    assert blocked.model_dump(mode="json", exclude_none=True) == {
        "tool_call_id": "call_01JXYZ",
        "subtask_id": "sub_01JXYZ",
        "status": "risk_blocked",
        "search_queries": [],
        "message": "触发风控敏感，请重新规划",
    }

    with pytest.raises(ValidationError):
        CollectSummary(
            tool_call_id="call_01JERR",
            subtask_id="sub_01JERR",
            status=CollectSummaryStatus.RISK_BLOCKED,
        )


def test_event_envelope_schema_matches_sse_contract() -> None:
    envelope = EventEnvelope(
        seq=41,
        event="planner.tool_call.requested",
        task_id="tsk_01JABC",
        revision_id=None,
        phase=TaskPhase.PLANNING_COLLECTION,
        timestamp=NOW,
        payload={},
    )

    assert envelope.model_dump(mode="json") == {
        "seq": 41,
        "event": "planner.tool_call.requested",
        "task_id": "tsk_01JABC",
        "revision_id": None,
        "phase": "planning_collection",
        "timestamp": "2026-03-15T12:00:00Z",
        "payload": {},
    }


def test_token_payload_models_capture_task_and_access_token_semantics() -> None:
    task_token = TaskTokenPayload(
        task_id="tsk_01JABC",
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=30),
    )
    access_token = AccessTokenPayload(
        task_id="tsk_01JABC",
        resource_type=AccessTokenResourceType.ARTIFACT,
        resource_scope="art_01JABC",
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
    )

    assert task_token.model_dump(mode="json") == {
        "task_id": "tsk_01JABC",
        "issued_at": "2026-03-15T12:00:00Z",
        "expires_at": "2026-03-15T12:30:00Z",
    }
    assert access_token.model_dump(mode="json") == {
        "task_id": "tsk_01JABC",
        "resource_type": "artifact",
        "resource_scope": "art_01JABC",
        "issued_at": "2026-03-15T12:00:00Z",
        "expires_at": "2026-03-15T12:10:00Z",
    }

    with pytest.raises(ValidationError):
        AccessTokenPayload(
            task_id="tsk_01JABC",
            resource_type=AccessTokenResourceType.ARTIFACT,
            resource_scope="art_01JABC",
            issued_at=NOW,
            expires_at=NOW,
        )
