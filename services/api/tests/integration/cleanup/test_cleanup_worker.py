import asyncio
from collections.abc import AsyncIterator
from dataclasses import replace
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.ports.delivery import ArtifactStore
from app.core.config import Settings
from app.infrastructure.db.models import ArtifactRecord, ResearchTaskRecord
from app.infrastructure.delivery.local import LocalArtifactStore
from app.main import create_app
from tests.contract.rest.test_task_events import assert_stream_closed, read_sse_event, read_until_event
from tests.fixtures.app import StreamingASGITransport
from tests.fixtures.runtime import FakeClock
from tests.fixtures.tasks import seed_delivered_task


class RecordingArtifactStore(LocalArtifactStore):
    def __init__(self, *, root_dir: Path, db_session: Session) -> None:
        super().__init__(root_dir=root_dir)
        self.db_session = db_session
        self.delete_checks: list[bool] = []

    async def delete(self, storage_key: str) -> None:
        self.db_session.expire_all()
        self.delete_checks.append(
            self.db_session.scalar(select(ResearchTaskRecord.task_id).limit(1)) is not None
        )
        await super().delete(storage_key)


class FlakyDeleteArtifactStore(LocalArtifactStore):
    def __init__(self, *, root_dir: Path) -> None:
        super().__init__(root_dir=root_dir)
        self.failures_remaining = 1

    async def delete(self, storage_key: str) -> None:
        if self.failures_remaining > 0:
            self.failures_remaining -= 1
            raise RuntimeError("temporary delete failure")
        await super().delete(storage_key)


@pytest_asyncio.fixture
async def make_cleanup_client(
    settings: Settings,
    fake_clock: FakeClock,
):
    apps_to_shutdown: list[FastAPI] = []

    async def _factory(
        *,
        artifact_store: ArtifactStore,
        cleanup_scan_interval_seconds: float = 0.02,
    ) -> tuple[FastAPI, AsyncClient]:
        app = create_app(
            settings=replace(
                settings,
                lifecycle_poll_interval_seconds=0.02,
                cleanup_scan_interval_seconds=cleanup_scan_interval_seconds,
            ),
            clock=fake_clock.now,
            artifact_store=artifact_store,
        )
        await app.router.startup()
        apps_to_shutdown.append(app)
        transport = StreamingASGITransport(app=app, client=("203.0.113.10", 51000))
        client = AsyncClient(transport=transport, base_url="http://testserver")
        return app, client

    yield _factory

    for app in reversed(apps_to_shutdown):
        await app.state.task_lifecycle.shutdown()
        await app.router.shutdown()


async def _wait_for_missing_task(
    db_session: Session,
    *,
    task_id: str,
    timeout: float = 1.0,
) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        db_session.expire_all()
        if db_session.get(ResearchTaskRecord, task_id) is None:
            return
        await asyncio.sleep(0.02)
    raise AssertionError("Timed out waiting for task cleanup.")


@pytest.mark.asyncio
async def test_expiry_after_30_minutes_emits_terminal_event_and_cleans_artifacts(
    make_cleanup_client,
    db_session: Session,
    fake_clock: FakeClock,
    temp_artifact_dir: Path,
) -> None:
    app, client = await make_cleanup_client(
        artifact_store=LocalArtifactStore(root_dir=temp_artifact_dir),
    )

    async with client:
        seeded = await seed_delivered_task(
            session=db_session,
            task_service=app.state.task_service,
            artifact_store=app.state.artifact_store,
            now=fake_clock.now(),
            suffix="cleanup_expiry",
        )
        async with client.stream(
            "GET",
            f"/api/v1/tasks/{seeded.task_id}/events",
            headers={"Authorization": f"Bearer {seeded.task_token}"},
        ) as response:
            lines = response.aiter_lines()
            await read_sse_event(lines)
            fake_clock.advance(minutes=31)
            _, event_name, _ = await read_until_event(lines, {"task.expired"}, timeout=2.0)
            await assert_stream_closed(lines)

        await _wait_for_missing_task(db_session, task_id=seeded.task_id, timeout=1.0)

        assert event_name == "task.expired"
        assert not (temp_artifact_dir / seeded.artifact_storage_key).exists()
        assert not (temp_artifact_dir / seeded.markdown_storage_key).exists()
        assert not (temp_artifact_dir / seeded.pdf_storage_key).exists()


@pytest.mark.asyncio
async def test_disconnect_marks_cleanup_pending_and_deletes_artifacts_before_db_rows(
    make_cleanup_client,
    db_session: Session,
    fake_clock: FakeClock,
    temp_artifact_dir: Path,
) -> None:
    artifact_store = RecordingArtifactStore(root_dir=temp_artifact_dir, db_session=db_session)
    app, client = await make_cleanup_client(artifact_store=artifact_store)

    async with client:
        seeded = await seed_delivered_task(
            session=db_session,
            task_service=app.state.task_service,
            artifact_store=app.state.artifact_store,
            now=fake_clock.now(),
            suffix="cleanup_disconnect",
        )
        async with client.stream(
            "GET",
            f"/api/v1/tasks/{seeded.task_id}/events",
            headers={"Authorization": f"Bearer {seeded.task_token}"},
        ) as response:
            lines = response.aiter_lines()
            await read_sse_event(lines)
            disconnect_response = await client.post(
                f"/api/v1/tasks/{seeded.task_id}/disconnect",
                headers={"Authorization": f"Bearer {seeded.task_token}"},
                json={"reason": "pagehide"},
            )
            _, event_name, _ = await read_until_event(lines, {"task.terminated"}, timeout=2.0)
            await assert_stream_closed(lines)

        await _wait_for_missing_task(db_session, task_id=seeded.task_id, timeout=1.0)

        assert disconnect_response.status_code == 202
        assert event_name == "task.terminated"
        assert artifact_store.delete_checks
        assert all(artifact_store.delete_checks)
        assert db_session.scalars(select(ArtifactRecord)).first() is None


@pytest.mark.asyncio
async def test_cleanup_expired_tasks_worker_retries_cleanup_pending_residual_tasks(
    make_cleanup_client,
    db_session: Session,
    fake_clock: FakeClock,
    temp_artifact_dir: Path,
) -> None:
    artifact_store = FlakyDeleteArtifactStore(root_dir=temp_artifact_dir)
    app, client = await make_cleanup_client(
        artifact_store=artifact_store,
        cleanup_scan_interval_seconds=60.0,
    )

    async with client:
        seeded = await seed_delivered_task(
            session=db_session,
            task_service=app.state.task_service,
            artifact_store=app.state.artifact_store,
            now=fake_clock.now(),
            suffix="cleanup_retry",
        )
        task = db_session.get(ResearchTaskRecord, seeded.task_id)
        assert task is not None
        task.status = "terminated"
        task.expires_at = fake_clock.now()
        task.updated_at = fake_clock.now()
        task.cleanup_pending = True
        db_session.commit()

        await app.state.task_lifecycle.run_cleanup_compensation()

        db_session.expire_all()
        remaining_task = db_session.get(ResearchTaskRecord, seeded.task_id)
        assert remaining_task is not None
        assert remaining_task.cleanup_pending is True
        assert (temp_artifact_dir / seeded.artifact_storage_key).exists()

        await app.state.task_lifecycle.run_cleanup_compensation()

        await _wait_for_missing_task(db_session, task_id=seeded.task_id, timeout=1.0)
        assert not (temp_artifact_dir / seeded.artifact_storage_key).exists()
