import pytest


@pytest.mark.asyncio
async def test_pytest_discovers_async_tests() -> None:
    async def minimal_async_work() -> str:
        return "ok"

    assert await minimal_async_work() == "ok"
