import pytest


@pytest.fixture
def db_engine() -> None:
    return None


@pytest.fixture
def db_session(db_engine: None) -> None:
    del db_engine
    return None
