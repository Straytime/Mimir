from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def allowed_origin() -> str:
    return "https://app.example.com"


@pytest.fixture
def denied_origin() -> str:
    return "https://denied.example.com"


@pytest.fixture
def settings(migrated_database_url: str, allowed_origin: str) -> Settings:
    return Settings(
        database_url=migrated_database_url,
        cors_allow_origins=(allowed_origin,),
        task_token_secret="task-secret",
        access_token_secret="access-secret",
    )


@pytest_asyncio.fixture
async def app_client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings=settings)
    await app.router.startup()

    transport = ASGITransport(app=app, client=("203.0.113.10", 51000))
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client

    await app.router.shutdown()
