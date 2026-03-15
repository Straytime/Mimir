import os
import subprocess
import tempfile
import uuid
from contextlib import suppress
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


POSTGRES_BIN_DIR = Path("/opt/homebrew/opt/postgresql@16/bin")


@pytest.fixture(scope="session")
def postgres_server(tmp_path_factory: pytest.TempPathFactory) -> str:
    if not POSTGRES_BIN_DIR.exists():
        raise RuntimeError("PostgreSQL 16 binaries are required for Stage 2 tests")

    data_dir = tmp_path_factory.mktemp("postgres-data")
    log_file = tmp_path_factory.mktemp("postgres-log") / "postgres.log"
    socket_dir = Path(tempfile.mkdtemp(prefix="mimir-pg-", dir="/tmp"))
    env = os.environ | {"LC_ALL": "C"}

    subprocess.run(
        [
            str(POSTGRES_BIN_DIR / "initdb"),
            "-D",
            str(data_dir),
            "-U",
            "postgres",
            "-A",
            "trust",
            "--no-locale",
            "--encoding=UTF8",
        ],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            str(POSTGRES_BIN_DIR / "pg_ctl"),
            "-D",
            str(data_dir),
            "-l",
            str(log_file),
            "-o",
            f"-F -k {socket_dir} -h ''",
            "start",
        ],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )

    try:
        yield f"postgresql+psycopg://postgres@/postgres?host={socket_dir}"
    finally:
        with suppress(subprocess.CalledProcessError):
            subprocess.run(
                [
                    str(POSTGRES_BIN_DIR / "pg_ctl"),
                    "-D",
                    str(data_dir),
                    "stop",
                    "-m",
                    "fast",
                ],
                check=True,
                env=env,
                capture_output=True,
                text=True,
            )
        socket_dir.rmdir()


@pytest.fixture
def database_url(postgres_server: str) -> str:
    database_name = f"mimir_test_{uuid.uuid4().hex[:12]}"
    admin_engine = create_engine(
        postgres_server,
        future=True,
        isolation_level="AUTOCOMMIT",
    )

    try:
        with admin_engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
        prefix, separator, suffix = postgres_server.partition("/postgres?host=")
        if not separator:
            raise RuntimeError("Unexpected PostgreSQL DSN format for Stage 2 tests")
        yield f"{prefix}/{database_name}?host={suffix}"
    finally:
        with admin_engine.connect() as connection:
            connection.exec_driver_sql(
                f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{database_name}'
                  AND pid <> pg_backend_pid()
                """,
            )
            connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{database_name}"')
        admin_engine.dispose()


@pytest.fixture
def alembic_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option(
        "script_location",
        "/Users/aminer/Library/CloudStorage/OneDrive-个人/projects/Mimir/services/api/app/infrastructure/db/migrations",
    )
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture
def migrated_database_url(alembic_config: Config, database_url: str) -> str:
    command.upgrade(alembic_config, "head")
    return database_url


@pytest.fixture
def db_engine(migrated_database_url: str) -> Engine:
    engine = create_engine(migrated_database_url, future=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Session:
    session_factory = sessionmaker(bind=db_engine, expire_on_commit=False, future=True)
    with session_factory() as session:
        yield session
