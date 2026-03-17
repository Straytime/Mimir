from pathlib import Path

from fastapi import FastAPI

from app.core.config import Settings
from app.infrastructure.delivery.local import LocalArtifactStore
from app.main import create_app


def test_create_app_builds_minimal_application() -> None:
    app = create_app()

    assert isinstance(app, FastAPI)
    assert app.title == "mimir-api"
    assert any(route.path == "/api/v1/health" for route in app.routes)


def test_create_app_uses_configured_artifact_root_dir(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            database_url="sqlite+pysqlite:///:memory:",
            artifact_root_dir=str(tmp_path),
        )
    )

    assert isinstance(app.state.artifact_store, LocalArtifactStore)
    assert app.state.artifact_store.root_dir == tmp_path
