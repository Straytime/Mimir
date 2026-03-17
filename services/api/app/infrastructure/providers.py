import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.application.ports.delivery import E2BSandboxClient, OutlineAgent, WriterAgent
from app.infrastructure.delivery.e2b import E2BRealSandboxClient
from app.application.ports.llm import (
    ClarificationGenerator,
    FeedbackAnalyzer,
    RequirementAnalyzer,
)
from app.application.ports.research import (
    CollectorAgent,
    PlannerAgent,
    SummaryAgent,
    WebFetchClient,
    WebSearchClient,
)
from app.core.config import Settings
from app.infrastructure.delivery.local import (
    LocalStubOutlineAgent,
    LocalStubSandboxClient,
    LocalStubWriterAgent,
)
from app.infrastructure.delivery.zhipu import ZhipuOutlineAgent, ZhipuWriterAgent
from app.infrastructure.llm.local_stub import (
    LocalStubClarificationGenerator,
    LocalStubFeedbackAnalyzer,
    LocalStubRequirementAnalyzer,
)
from app.infrastructure.llm.zhipu import (
    ZhipuChatClient,
    ZhipuClarificationGenerator,
    ZhipuFeedbackAnalyzer,
    ZhipuRequirementAnalyzer,
    create_default_zhipu_client,
)
from app.infrastructure.research.local_stub import (
    LocalStubCollectorAgent,
    LocalStubPlannerAgent,
    LocalStubSummaryAgent,
    LocalStubWebFetchClient,
    LocalStubWebSearchClient,
)
from app.infrastructure.research.jina import JinaWebFetchClient
from app.infrastructure.research.real_http import (
    ZhipuCollectorAgent,
    ZhipuPlannerAgent,
    ZhipuSummaryAgent,
    ZhipuWebSearchClient,
)


CleanupCallback = Callable[[], Awaitable[None] | None]


@dataclass(slots=True)
class ProviderRuntime:
    clarification_generator: ClarificationGenerator
    requirement_analyzer: RequirementAnalyzer
    feedback_analyzer: FeedbackAnalyzer
    planner_agent: PlannerAgent
    collector_agent: CollectorAgent
    summary_agent: SummaryAgent
    web_search_client: WebSearchClient
    web_fetch_client: WebFetchClient
    outline_agent: OutlineAgent
    writer_agent: WriterAgent
    sandbox_client: E2BSandboxClient
    _cleanup_callbacks: tuple[CleanupCallback, ...] = ()

    async def shutdown(self) -> None:
        for callback in self._cleanup_callbacks:
            result = callback()
            if inspect.isawaitable(result):
                await result


def build_provider_runtime(settings: Settings) -> ProviderRuntime:
    settings.validate_provider_configuration()

    llm_mode = settings.resolved_llm_provider_mode()
    web_search_mode = settings.resolved_web_search_provider_mode()
    web_fetch_mode = settings.resolved_web_fetch_provider_mode()
    e2b_mode = settings.resolved_e2b_provider_mode()
    cleanup_callbacks: list[CleanupCallback] = []

    if llm_mode == "real":
        zhipu_client = ZhipuChatClient(
            client=create_default_zhipu_client(
                api_key=settings.zhipu_api_key or "",
                base_url=settings.zhipu_base_url,
                timeout_seconds=settings.zhipu_timeout_seconds,
            )
        )
        clarification_generator: ClarificationGenerator = ZhipuClarificationGenerator(
            client=zhipu_client,
            natural_model=settings.zhipu_clarification_natural_model,
            options_model=settings.zhipu_clarification_options_model,
        )
        requirement_analyzer: RequirementAnalyzer = ZhipuRequirementAnalyzer(
            client=zhipu_client,
            model=settings.zhipu_requirement_analyzer_model,
        )
        feedback_analyzer: FeedbackAnalyzer = ZhipuFeedbackAnalyzer(
            client=zhipu_client,
            model=settings.zhipu_feedback_analyzer_model,
        )
        planner_agent: PlannerAgent = ZhipuPlannerAgent(
            client=zhipu_client,
            model=settings.zhipu_planner_model,
        )
        collector_agent: CollectorAgent = ZhipuCollectorAgent(
            client=zhipu_client,
            model=settings.zhipu_collector_model,
        )
        summary_agent: SummaryAgent = ZhipuSummaryAgent(
            client=zhipu_client,
            model=settings.zhipu_summary_model,
        )
        outline_agent: OutlineAgent = ZhipuOutlineAgent(
            client=zhipu_client,
            model=settings.zhipu_outline_model,
        )
        writer_agent: WriterAgent = ZhipuWriterAgent(
            client=zhipu_client,
            model=settings.zhipu_writer_model,
        )
    else:
        clarification_generator = LocalStubClarificationGenerator()
        requirement_analyzer = LocalStubRequirementAnalyzer()
        feedback_analyzer = LocalStubFeedbackAnalyzer()
        planner_agent = LocalStubPlannerAgent()
        collector_agent = LocalStubCollectorAgent()
        summary_agent = LocalStubSummaryAgent()
        outline_agent = LocalStubOutlineAgent()
        writer_agent = LocalStubWriterAgent()

    if web_search_mode == "real":
        web_search_client = ZhipuWebSearchClient(
            api_key=settings.zhipu_api_key or "",
            base_url=settings.zhipu_base_url,
            endpoint_path=settings.web_search_endpoint_path,
            engine=settings.web_search_engine,
            timeout_seconds=settings.web_search_timeout_seconds,
        )
        cleanup_callbacks.append(web_search_client.aclose)
    else:
        web_search_client = LocalStubWebSearchClient()

    if web_fetch_mode == "real":
        web_fetch_client = JinaWebFetchClient(
            api_key=settings.jina_api_key or "",
            base_url=settings.jina_base_url,
            timeout_seconds=settings.web_fetch_timeout_seconds,
        )
        cleanup_callbacks.append(web_fetch_client.aclose)
    else:
        web_fetch_client = LocalStubWebFetchClient()

    if e2b_mode == "real":
        sandbox_client = E2BRealSandboxClient(
            api_key=settings.e2b_api_key or "",
            request_timeout_seconds=settings.e2b_request_timeout_seconds,
            execution_timeout_seconds=settings.e2b_execution_timeout_seconds,
            sandbox_timeout_seconds=settings.e2b_sandbox_timeout_seconds,
        )
        cleanup_callbacks.append(sandbox_client.shutdown)
    else:
        sandbox_client = LocalStubSandboxClient()

    return ProviderRuntime(
        clarification_generator=clarification_generator,
        requirement_analyzer=requirement_analyzer,
        feedback_analyzer=feedback_analyzer,
        planner_agent=planner_agent,
        collector_agent=collector_agent,
        summary_agent=summary_agent,
        web_search_client=web_search_client,
        web_fetch_client=web_fetch_client,
        outline_agent=outline_agent,
        writer_agent=writer_agent,
        sandbox_client=sandbox_client,
        _cleanup_callbacks=tuple(cleanup_callbacks),
    )
