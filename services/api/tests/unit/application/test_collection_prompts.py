from app.application.dto.invocation import PromptMessage
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
    assert "2.1 若无法支撑：" in prompt.system_prompt
    assert "2.2 若能够支撑" in prompt.system_prompt
    assert "你并不需要一次性理清所有目标，而是根据已有信息进行动态规划。" in prompt.system_prompt
    assert "发起 `collect_agent` 调用时保证目标与约束自包含" in prompt.system_prompt
    assert "提供必要、精准的补充描述信息和背景" in prompt.system_prompt
    assert "不能假设 agent 拥有任何预设上下文。" in prompt.system_prompt
    assert "尤其是在你还未搞清研究主体的时候" in prompt.system_prompt
    assert "避免多个目标之间存在交叉和重叠" in prompt.system_prompt
    assert "最多只能同时发起 3 个`collect_agent`工具调用。" in prompt.system_prompt
    assert "必须主动停止搜集" in prompt.system_prompt
    assert "**绝不能超过 9 次工具调用**" in prompt.system_prompt
    assert "collect_agent" in prompt.system_prompt
    assert "2026-03-16" in prompt.system_prompt
    assert "分析中国 AI 搜索产品的竞争格局与机会" in prompt.user_prompt
    assert [message.role for message in prompt.transcript] == ["assistant", "tool", "tool"]
    assistant_msg = prompt.transcript[0]
    assert assistant_msg.tool_calls is not None
    assert len(assistant_msg.tool_calls) == 2
    assert [tc["id"] for tc in assistant_msg.tool_calls] == ["call_1", "call_2"]
    tool_msgs = [m for m in prompt.transcript if m.role == "tool"]
    assert [m.tool_call_id for m in tool_msgs] == ["call_1", "call_2"]
    assert "收集目标 1" in tool_msgs[0].content
    assert "收集目标 2" in tool_msgs[1].content


def test_collector_prompt_semantic_lock_matches_current_wording_and_transcript() -> None:
    prompt = build_collector_prompt(
        invocation=CollectorInvocation(
            prompt_name="collector_round",
            subtask_id="sub_1",
            plan=build_collect_plan(),
            call_index=1,
            tool_call_limit=10,
            now=NOW,
            transcript=(
                PromptMessage(
                    role="assistant",
                    content="",
                    reasoning_content="先搜一次。",
                    tool_calls=(
                        {
                            "id": "call_search_1",
                            "type": "function",
                            "function": {
                                "name": "web_search",
                                "arguments": '{"search_query":"收集目标 1","search_recency_filter":"oneWeek"}',
                            },
                        },
                    ),
                ),
            ),
        )
    )

    assert "你是一个信息搜集 agent" in prompt.system_prompt
    assert "负责进行信息的搜集以达成特定的信息获取目标，并将搜集结果进行整理输出" in prompt.system_prompt
    assert "你的输出将被用于深度研究内容撰写" in prompt.system_prompt
    assert "`web_search` 和 `web_fetch`" in prompt.system_prompt
    assert "你最多只能调用 10 次工具" in prompt.system_prompt
    assert "1. 仔细观察信息获取目标、补充信息和工具返回的执行结果" in prompt.system_prompt
    assert "2.1 若无法支撑：" in prompt.system_prompt
    assert "规划接下来要执行的信息搜集行为" in prompt.system_prompt
    assert "调用 `web_search` 或 `web_fetch` 工具执行" in prompt.system_prompt
    assert "2.2 若能够支撑" in prompt.system_prompt
    assert "只要 total_tool_calls = 10" in prompt.system_prompt
    assert "必须主动停止搜集" in prompt.system_prompt
    assert "停止搜集，基于已有信息输出整理后的信息搜集结果" in prompt.system_prompt
    assert "尽最大可能保留和目标相关的高质量信息和数据" in prompt.system_prompt
    assert "原始网页 link 和 title" in prompt.system_prompt
    assert "**绝不能超过 10 次工具调用。**" in prompt.system_prompt
    assert "<最终输出格式>" in prompt.system_prompt
    assert '"info":""' in prompt.system_prompt
    assert '"title":""' in prompt.system_prompt
    assert '"link":""' in prompt.system_prompt
    assert "<信息获取目标>" in prompt.user_prompt
    assert "收集目标 1" in prompt.user_prompt
    assert "优先官方发布与高可信媒体。" in prompt.user_prompt
    assert "<时效要求>" in prompt.user_prompt
    assert "high" in prompt.user_prompt
    assert prompt.transcript[0].reasoning_content == "先搜一次。"
    assert prompt.transcript[0].tool_calls is not None


def test_summary_prompt_semantic_lock_keeps_schema_and_runtime_inputs() -> None:
    prompt = build_summary_prompt(
        invocation=SummaryInvocation(
            prompt_name="summary_round",
            subtask_id="sub_1",
            plan=build_collect_plan(),
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
    assert "提取不超过10条关键发现" in prompt.system_prompt
    assert "只做客观的信息总结与压缩" in prompt.system_prompt
    assert "如果搜集结果中没有任何相关内容，如实声明" in prompt.system_prompt
    assert "严禁给出高度抽象的一句话总结" in prompt.system_prompt
    assert "严禁给出任何指引或建议" in prompt.system_prompt
    assert "markdown 无序列表格式直接输出" in prompt.system_prompt
    assert "<信息获取目标>" in prompt.user_prompt
    assert "收集目标 1" in prompt.user_prompt
    assert "中国 AI 搜索 产品 2025" in prompt.user_prompt
    assert "某公司发布会回顾" in prompt.user_prompt
    assert "<搜集状态>" not in prompt.user_prompt
    assert "completed" not in prompt.user_prompt
