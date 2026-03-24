from app.core.config import Settings
from app.core.database_url import normalize_database_url, resolve_database_url_from_env


def test_settings_from_env_uses_railway_volume_mount_for_artifacts(
    monkeypatch,
) -> None:
    monkeypatch.delenv("MIMIR_ARTIFACT_ROOT_DIR", raising=False)
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", "/var/lib/railway/volume")

    settings = Settings.from_env()

    assert settings.artifact_root_dir == "/var/lib/railway/volume/mimir-artifacts"


def test_settings_from_env_accepts_database_url_fallback(monkeypatch) -> None:
    monkeypatch.delenv("MIMIR_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://postgres@db:5432/mimir")

    settings = Settings.from_env()

    assert settings.database_url == "postgresql+psycopg://postgres@db:5432/mimir"


def test_settings_from_env_normalizes_railway_database_url(monkeypatch) -> None:
    monkeypatch.delenv("MIMIR_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:secret@db.railway.internal:5432/railway")

    settings = Settings.from_env()

    assert (
        settings.database_url
        == "postgresql+psycopg://postgres:secret@db.railway.internal:5432/railway"
    )


def test_settings_from_env_uses_default_writer_max_rounds(monkeypatch) -> None:
    monkeypatch.delenv("MIMIR_WRITER_MAX_ROUNDS", raising=False)

    settings = Settings.from_env()

    assert settings.writer_max_rounds == 5


def test_settings_from_env_reads_writer_max_rounds(monkeypatch) -> None:
    monkeypatch.setenv("MIMIR_WRITER_MAX_ROUNDS", "7")

    settings = Settings.from_env()

    assert settings.writer_max_rounds == 7


def test_settings_from_env_uses_default_fetched_content_limit(monkeypatch) -> None:
    monkeypatch.delenv("MIMIR_FETCHED_CONTENT_LIMIT", raising=False)

    settings = Settings.from_env()

    assert settings.fetched_content_limit == 5000


def test_settings_from_env_reads_fetched_content_limit(monkeypatch) -> None:
    monkeypatch.setenv("MIMIR_FETCHED_CONTENT_LIMIT", "4321")

    settings = Settings.from_env()

    assert settings.fetched_content_limit == 4321


def test_settings_from_env_reads_e2b_template(monkeypatch) -> None:
    monkeypatch.setenv("MIMIR_E2B_TEMPLATE", "mimir-cjk-template")

    settings = Settings.from_env()

    assert settings.e2b_template == "mimir-cjk-template"


def test_settings_from_env_uses_default_llm_trace_retention_hours(monkeypatch) -> None:
    monkeypatch.delenv("MIMIR_LLM_TRACE_RETENTION_HOURS", raising=False)

    settings = Settings.from_env()

    assert settings.llm_trace_retention_hours == 72


def test_settings_from_env_reads_llm_trace_retention_hours(monkeypatch) -> None:
    monkeypatch.setenv("MIMIR_LLM_TRACE_RETENTION_HOURS", "96")

    settings = Settings.from_env()

    assert settings.llm_trace_retention_hours == 96


def test_resolve_database_url_from_env_prefers_mimir_database_url(monkeypatch) -> None:
    monkeypatch.setenv(
        "MIMIR_DATABASE_URL",
        "postgres://postgres:secret@mimir-db:5432/mimir",
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:secret@railway-db:5432/railway",
    )

    assert (
        resolve_database_url_from_env()
        == "postgresql+psycopg://postgres:secret@mimir-db:5432/mimir"
    )


def test_normalize_database_url_keeps_explicit_driver() -> None:
    assert (
        normalize_database_url("postgresql+psycopg://postgres@db:5432/mimir")
        == "postgresql+psycopg://postgres@db:5432/mimir"
    )
