import json

from app.application.dto.research import (
    CollectorInvocation,
    PlannerInvocation,
    SummaryInvocation,
)


def build_planner_prompt(*, invocation: PlannerInvocation) -> str:
    return f"""
你是 Mimir 的 master planner。
当前时间: {invocation.now.isoformat()}
当前 collect_agent 已使用次数: {invocation.collect_agent_calls_used}
RequirementDetail:
{json.dumps(invocation.requirement_detail.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2)}
已有 CollectSummary:
{json.dumps([summary.model_dump(mode="json", exclude_none=True) for summary in invocation.summaries], ensure_ascii=False, indent=2)}

要求：
- 单轮最多 3 个 CollectPlan
- 单个 Revision 累计最多 5 次 collect_agent
- 只输出 stop 或 CollectPlan[]
- CollectPlan 必须包含 collect_target / additional_info / freshness_requirement
""".strip()


def build_collector_prompt(*, invocation: CollectorInvocation) -> str:
    return f"""
你是 Mimir 的 collect sub-agent。
当前时间: {invocation.now.isoformat()}
SubTask: {invocation.subtask_id}
CollectTarget: {invocation.plan.collect_target}
AdditionalInfo: {invocation.plan.additional_info}
FreshnessRequirement: {invocation.plan.freshness_requirement.value}

要求：
- 最多 10 次工具调用
- 工具只有 web_search 和 web_fetch
- search_recency_filter 使用 noLimit
- 先规划搜索查询，再决定抓取哪些 URL
""".strip()


def build_summary_prompt(*, invocation: SummaryInvocation) -> str:
    return f"""
你是 Mimir 的 summary orchestrator。
当前时间: {invocation.now.isoformat()}
SubTask: {invocation.subtask_id}
CollectTarget: {invocation.plan.collect_target}
CollectResultStatus: {invocation.result_status}
SearchQueries:
{json.dumps(list(invocation.search_queries), ensure_ascii=False, indent=2)}
Items:
{json.dumps(list(invocation.item_payloads), ensure_ascii=False, indent=2)}

要求：
- 只输出压缩摘要正文
- 最终结构必须能映射为 CollectSummary
- 若信息不足可返回 partial
- 若触发风险则必须返回 risk_blocked
""".strip()
