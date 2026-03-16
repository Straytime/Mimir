from app.application.dto.research import (
    CollectorDecision,
    CollectorInvocation,
    FetchResponse,
    PlannerDecision,
    PlannerInvocation,
    SearchHit,
    SearchResponse,
    SummaryDecision,
    SummaryInvocation,
)
from app.domain.enums import CollectSummaryStatus, FreshnessRequirement
from app.domain.schemas import CollectPlan


class LocalStubPlannerAgent:
    async def plan(self, invocation: PlannerInvocation) -> PlannerDecision:
        if invocation.call_index == 1:
            return PlannerDecision(
                reasoning_deltas=("当前还缺少代表性玩家与市场趋势信息。",),
                plans=(
                    CollectPlan(
                        tool_call_id="call_local_1",
                        revision_id=invocation.summaries[0].tool_call_id
                        if invocation.summaries
                        else "rev_placeholder",
                        collect_target="收集 2024-2026 年中国 AI 搜索产品的主要厂商与公开进展",
                        additional_info="优先官方发布与高可信媒体。",
                        freshness_requirement=FreshnessRequirement.HIGH,
                    ),
                ),
                stop=False,
            )

        return PlannerDecision(
            reasoning_deltas=("当前信息已足够进入 source merge。",),
            plans=(),
            stop=True,
        )


class LocalStubCollectorAgent:
    async def plan(self, invocation: CollectorInvocation) -> CollectorDecision:
        return CollectorDecision(
            reasoning_deltas=("先做高时效搜索，再读取官方来源。",),
            search_queries=("中国 AI 搜索 产品 2025",),
            search_recency_filter="noLimit",
        )


class LocalStubSummaryAgent:
    async def summarize(self, invocation: SummaryInvocation) -> SummaryDecision:
        return SummaryDecision(
            status=CollectSummaryStatus.COMPLETED,
            key_findings_markdown="- 官方披露更多集中在 2025 年后。",
        )


class LocalStubWebSearchClient:
    async def search(self, query: str, recency_filter: str) -> SearchResponse:
        return SearchResponse(
            query=query,
            recency_filter="noLimit" if recency_filter.lower() == "nolimit" else recency_filter,
            results=(
                SearchHit(
                    title="某公司发布会回顾",
                    link="https://example.com/article",
                    snippet="某产品在 2025 年发布企业版能力。",
                ),
            ),
        )


class LocalStubWebFetchClient:
    async def fetch(self, url: str) -> FetchResponse:
        return FetchResponse(
            url=url,
            success=True,
            title="某公司发布会回顾",
            content="某产品在 2025 年发布企业版能力，主要面向金融和政企客户。",
        )
