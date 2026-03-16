from typing import Protocol

from app.application.dto.research import (
    CollectorDecision,
    CollectorInvocation,
    FetchResponse,
    PlannerDecision,
    PlannerInvocation,
    SearchResponse,
    SummaryDecision,
    SummaryInvocation,
)


class PlannerAgent(Protocol):
    async def plan(self, invocation: PlannerInvocation) -> PlannerDecision: ...


class CollectorAgent(Protocol):
    async def plan(self, invocation: CollectorInvocation) -> CollectorDecision: ...


class SummaryAgent(Protocol):
    async def summarize(self, invocation: SummaryInvocation) -> SummaryDecision: ...


class WebSearchClient(Protocol):
    async def search(self, query: str, recency_filter: str) -> SearchResponse: ...


class WebFetchClient(Protocol):
    async def fetch(self, url: str) -> FetchResponse: ...
