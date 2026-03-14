from fastapi import FastAPI

from app.main import create_app


def test_create_app_builds_minimal_application() -> None:
    app = create_app()

    assert isinstance(app, FastAPI)
    assert app.title == "mimir-api"
    assert any(route.path == "/api/v1/health" for route in app.routes)
