from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class Settings:
    service_name: str = "mimir-api"
    service_version: str = "v1"
    database_url: str = "postgresql+psycopg://postgres@127.0.0.1:5432/postgres"
    cors_allow_origins: tuple[str, ...] = ("http://localhost:3000",)
    task_token_secret: str = "task-secret"
    access_token_secret: str = "access-secret"
    ip_quota_limit: int = 3
    ip_quota_window_hours: int = 24
    connect_deadline_seconds: int = 10
    sse_heartbeat_interval_seconds: int = 15
    client_heartbeat_timeout_seconds: int = 45
    lifecycle_poll_interval_seconds: float = 1.0
    task_token_ttl_hours: int = 24
    access_token_ttl_minutes: int = 10

    @classmethod
    def from_env(cls) -> "Settings":
        cors_allow_origins = tuple(
            origin.strip()
            for origin in os.getenv(
                "MIMIR_CORS_ALLOW_ORIGINS",
                "http://localhost:3000",
            ).split(",")
            if origin.strip()
        )
        return cls(
            service_name=os.getenv("MIMIR_SERVICE_NAME", "mimir-api"),
            service_version=os.getenv("MIMIR_SERVICE_VERSION", "v1"),
            database_url=os.getenv(
                "MIMIR_DATABASE_URL",
                "postgresql+psycopg://postgres@127.0.0.1:5432/postgres",
            ),
            cors_allow_origins=cors_allow_origins or ("http://localhost:3000",),
            task_token_secret=os.getenv("MIMIR_TASK_TOKEN_SECRET", "task-secret"),
            access_token_secret=os.getenv(
                "MIMIR_ACCESS_TOKEN_SECRET",
                "access-secret",
            ),
            ip_quota_limit=int(os.getenv("MIMIR_IP_QUOTA_LIMIT", "3")),
            ip_quota_window_hours=int(
                os.getenv("MIMIR_IP_QUOTA_WINDOW_HOURS", "24")
            ),
            connect_deadline_seconds=int(
                os.getenv("MIMIR_CONNECT_DEADLINE_SECONDS", "10")
            ),
            sse_heartbeat_interval_seconds=int(
                os.getenv("MIMIR_SSE_HEARTBEAT_INTERVAL_SECONDS", "15")
            ),
            client_heartbeat_timeout_seconds=int(
                os.getenv("MIMIR_CLIENT_HEARTBEAT_TIMEOUT_SECONDS", "45")
            ),
            lifecycle_poll_interval_seconds=float(
                os.getenv("MIMIR_LIFECYCLE_POLL_INTERVAL_SECONDS", "1.0")
            ),
            task_token_ttl_hours=int(
                os.getenv("MIMIR_TASK_TOKEN_TTL_HOURS", "24")
            ),
            access_token_ttl_minutes=int(
                os.getenv("MIMIR_ACCESS_TOKEN_TTL_MINUTES", "10")
            ),
        )
