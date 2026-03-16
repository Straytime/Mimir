from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.application.ports.delivery import ArtifactStore
from app.application.services.tasks import TaskService
from app.infrastructure.streaming.broker import TaskLifecycleManager


def get_db_session(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    with session_factory() as session:
        yield session


def get_task_service(request: Request) -> TaskService:
    return request.app.state.task_service


def get_task_lifecycle(request: Request) -> TaskLifecycleManager:
    return request.app.state.task_lifecycle


def get_artifact_store(request: Request) -> ArtifactStore:
    return request.app.state.artifact_store
