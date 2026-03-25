from contextlib import asynccontextmanager
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI

from app.api.error_handlers import register_error_handlers
from app.api.v1.router import api_v1_router
from app.api.middleware import install_middlewares
from app.application.policies.activity_lock import ActivityLockPolicy
from app.application.policies.ip_quota import IPQuotaPolicy
from app.application.ports.delivery import (
    ArtifactStore,
    E2BSandboxClient,
    OutlineAgent,
    ReportExportService,
    WriterAgent,
)
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
from app.application.services.collection import CollectionOrchestrator
from app.application.services.clarification import ClarificationOrchestrator
from app.application.services.delivery import DeliveryOrchestrator
from app.application.services.feedback import FeedbackOrchestrator
from app.application.services.invocation import RetryingOperationInvoker
from app.application.services.llm import RetryingLLMInvoker
from app.application.services.merge import SourceMergeService
from app.application.services.tasks import TaskService
from app.core.config import Settings
from app.core.logging import setup_logging
from app.core.retry import RetryPolicy
from app.infrastructure.db.repositories import TaskRepository
from app.infrastructure.db.session import create_session_factory
from app.infrastructure.delivery.local import (
    LocalArtifactStore,
    LocalReportExportService,
    LocalStubOutlineAgent,
    LocalStubWriterAgent,
)
from app.infrastructure.llm.local_stub import (
    LocalStubClarificationGenerator,
    LocalStubFeedbackAnalyzer,
    LocalStubRequirementAnalyzer,
)
from app.infrastructure.providers import build_provider_runtime
from app.infrastructure.security.hmac_signers import (
    HMACAccessTokenSigner,
    HMACTaskTokenSigner,
)
from app.infrastructure.streaming.broker import TaskLifecycleManager


def create_app(
    settings: Settings | None = None,
    *,
    clock: Callable[[], datetime] | None = None,
    clarification_generator: ClarificationGenerator | None = None,
    requirement_analyzer: RequirementAnalyzer | None = None,
    feedback_analyzer: FeedbackAnalyzer | None = None,
    planner_agent: PlannerAgent | None = None,
    collector_agent: CollectorAgent | None = None,
    summary_agent: SummaryAgent | None = None,
    web_search_client: WebSearchClient | None = None,
    web_fetch_client: WebFetchClient | None = None,
    outline_agent: OutlineAgent | None = None,
    writer_agent: WriterAgent | None = None,
    sandbox_client: E2BSandboxClient | None = None,
    artifact_store: ArtifactStore | None = None,
    report_export_service: ReportExportService | None = None,
) -> FastAPI:
    setup_logging()
    resolved_settings = settings or Settings.from_env()
    engine, session_factory = create_session_factory(resolved_settings.database_url)
    resolved_clock = clock or (lambda: datetime.now(UTC))

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            await application.state.task_lifecycle.shutdown()
            await application.state.provider_runtime.shutdown()
            engine.dispose()

    application = FastAPI(
        title=resolved_settings.service_name,
        version=resolved_settings.service_version,
        lifespan=lifespan,
    )
    provider_runtime = build_provider_runtime(resolved_settings)
    application.state.settings = resolved_settings
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.state.provider_runtime = provider_runtime
    application.state.artifact_store = artifact_store or LocalArtifactStore(
        root_dir=Path(resolved_settings.artifact_root_dir)
        if resolved_settings.artifact_root_dir
        else None
    )
    application.state.task_service = TaskService(
        repository=TaskRepository(),
        task_token_signer=HMACTaskTokenSigner(
            secret=resolved_settings.task_token_secret,
            clock=resolved_clock,
        ),
        access_token_signer=HMACAccessTokenSigner(
            secret=resolved_settings.access_token_secret,
            clock=resolved_clock,
        ),
        activity_lock_policy=ActivityLockPolicy(),
        ip_quota_policy=IPQuotaPolicy(
            limit=resolved_settings.ip_quota_limit,
            window=timedelta(hours=resolved_settings.ip_quota_window_hours),
        ),
        settings=resolved_settings,
        clock=resolved_clock,
    )
    llm_invoker = RetryingLLMInvoker(
        retry_policy=RetryPolicy(
            max_retries=resolved_settings.llm_retry_max_retries,
            wait_seconds=resolved_settings.llm_retry_wait_seconds,
            backoff_multiplier=resolved_settings.llm_retry_backoff_multiplier,
            max_wait_seconds=resolved_settings.llm_retry_max_wait_seconds,
        )
    )
    operation_invoker = RetryingOperationInvoker[object](
        retry_policy=RetryPolicy(
            max_retries=resolved_settings.llm_retry_max_retries,
            wait_seconds=resolved_settings.llm_retry_wait_seconds,
            backoff_multiplier=resolved_settings.llm_retry_backoff_multiplier,
            max_wait_seconds=resolved_settings.llm_retry_max_wait_seconds,
        )
    )
    delivery_orchestrator = DeliveryOrchestrator(
        session_factory=session_factory,
        task_service=application.state.task_service,
        outline_agent=outline_agent or provider_runtime.outline_agent,
        writer_agent=writer_agent or provider_runtime.writer_agent,
        sandbox_client=sandbox_client or provider_runtime.sandbox_client,
        artifact_store=application.state.artifact_store,
        report_export_service=report_export_service or LocalReportExportService(),
        operation_invoker=operation_invoker,
        settings=resolved_settings,
        clock=resolved_clock,
    )
    application.state.delivery_orchestrator = delivery_orchestrator
    collection_orchestrator = CollectionOrchestrator(
        session_factory=session_factory,
        task_service=application.state.task_service,
        planner_agent=planner_agent or provider_runtime.planner_agent,
        collector_agent=collector_agent or provider_runtime.collector_agent,
        summary_agent=summary_agent or provider_runtime.summary_agent,
        web_search_client=web_search_client or provider_runtime.web_search_client,
        web_fetch_client=web_fetch_client or provider_runtime.web_fetch_client,
        operation_invoker=operation_invoker,
        merge_service=SourceMergeService(),
        settings=resolved_settings,
        on_sources_merged=lambda task_id: delivery_orchestrator.ensure_started(
            task_id=task_id
        ),
        clock=resolved_clock,
    )
    application.state.collection_orchestrator = collection_orchestrator
    feedback_orchestrator = FeedbackOrchestrator(
        session_factory=session_factory,
        task_service=application.state.task_service,
        feedback_analyzer=feedback_analyzer or provider_runtime.feedback_analyzer,
        llm_invoker=llm_invoker,
        on_feedback_completed=lambda task_id: collection_orchestrator.ensure_started(
            task_id=task_id
        ),
        clock=resolved_clock,
    )
    application.state.feedback_orchestrator = feedback_orchestrator
    clarification_orchestrator = ClarificationOrchestrator(
        session_factory=session_factory,
        task_service=application.state.task_service,
        clarification_generator=clarification_generator
        or provider_runtime.clarification_generator,
        requirement_analyzer=requirement_analyzer
        or provider_runtime.requirement_analyzer,
        web_search_client=web_search_client or provider_runtime.web_search_client,
        llm_invoker=llm_invoker,
        operation_invoker=operation_invoker,
        settings=resolved_settings,
        on_requirement_completed=lambda task_id: collection_orchestrator.ensure_started(
            task_id=task_id
        ),
        clock=resolved_clock,
    )
    application.state.clarification_orchestrator = clarification_orchestrator
    application.state.task_lifecycle = TaskLifecycleManager(
        session_factory=session_factory,
        task_service=application.state.task_service,
        clarification_orchestrator=clarification_orchestrator,
        collection_orchestrator=collection_orchestrator,
        delivery_orchestrator=delivery_orchestrator,
        feedback_orchestrator=feedback_orchestrator,
        artifact_store=application.state.artifact_store,
        sandbox_client=sandbox_client or provider_runtime.sandbox_client,
        operation_invoker=operation_invoker,
        settings=resolved_settings,
        clock=resolved_clock,
    )
    install_middlewares(application, settings=resolved_settings)
    register_error_handlers(application)
    application.include_router(api_v1_router)

    return application


app = create_app()
