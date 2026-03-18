import os


DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:5432/postgres"


def normalize_database_url(database_url: str) -> str:
    value = database_url.strip()
    lowered = value.lower()
    if lowered.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://") :]
    if lowered.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://") :]
    return value


def resolve_database_url_from_env() -> str:
    return normalize_database_url(
        os.getenv("MIMIR_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or DEFAULT_DATABASE_URL
    )
