import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_returns_minimal_contract(
    app_client: AsyncClient,
) -> None:
    response = await app_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "status": "ok",
        "service": "mimir-api",
        "version": "v1",
    }
