from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.application.services.tasks import TaskService


def get_db_session(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    with session_factory() as session:
        yield session


def get_task_service(request: Request) -> TaskService:
    return request.app.state.task_service
