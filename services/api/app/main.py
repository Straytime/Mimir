from contextlib import asynccontextmanager
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI

from app.api.error_handlers import register_error_handlers
from app.api.v1.router import api_v1_router
from app.api.middleware import install_middlewares
from app.application.policies.activity_lock import ActivityLockPolicy
from app.application.policies.ip_quota import IPQuotaPolicy
from app.application.services.tasks import TaskService
from app.core.config import Settings
from app.infrastructure.db.repositories import TaskRepository
from app.infrastructure.db.session import create_session_factory
from app.infrastructure.security.hmac_signers import (
    HMACAccessTokenSigner,
    HMACTaskTokenSigner,
)
from app.infrastructure.streaming.broker import TaskLifecycleManager


def create_app(
    settings: Settings | None = None,
    *,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    engine, session_factory = create_session_factory(resolved_settings.database_url)
    resolved_clock = clock or (lambda: datetime.now(UTC))

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            await application.state.task_lifecycle.shutdown()
            engine.dispose()

    application = FastAPI(
        title=resolved_settings.service_name,
        version=resolved_settings.service_version,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.engine = engine
    application.state.session_factory = session_factory
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
    application.state.task_lifecycle = TaskLifecycleManager(
        session_factory=session_factory,
        task_service=application.state.task_service,
        settings=resolved_settings,
        clock=resolved_clock,
    )
    install_middlewares(application, settings=resolved_settings)
    register_error_handlers(application)
    application.include_router(api_v1_router)

    return application


app = create_app()
