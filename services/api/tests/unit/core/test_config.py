from app.core.config import Settings


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
