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
    clarification_countdown_seconds: int = 15
    clarification_backend_timeout_seconds: int = 60
    llm_retry_max_retries: int = 3
    llm_retry_wait_seconds: int = 3
    planner_parallel_limit: int = 3
    revision_collect_agent_limit: int = 5
    subtask_tool_call_limit: int = 10
    collect_risk_block_threshold: int = 2
    fetched_content_limit: int = 10000
    cleanup_scan_interval_seconds: float = 60.0

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
            clarification_countdown_seconds=int(
                os.getenv("MIMIR_CLARIFICATION_COUNTDOWN_SECONDS", "15")
            ),
            clarification_backend_timeout_seconds=int(
                os.getenv("MIMIR_CLARIFICATION_BACKEND_TIMEOUT_SECONDS", "60")
            ),
            llm_retry_max_retries=int(
                os.getenv("MIMIR_LLM_RETRY_MAX_RETRIES", "3")
            ),
            llm_retry_wait_seconds=int(
                os.getenv("MIMIR_LLM_RETRY_WAIT_SECONDS", "3")
            ),
            planner_parallel_limit=int(
                os.getenv("MIMIR_PLANNER_PARALLEL_LIMIT", "3")
            ),
            revision_collect_agent_limit=int(
                os.getenv("MIMIR_REVISION_COLLECT_AGENT_LIMIT", "5")
            ),
            subtask_tool_call_limit=int(
                os.getenv("MIMIR_SUBTASK_TOOL_CALL_LIMIT", "10")
            ),
            collect_risk_block_threshold=int(
                os.getenv("MIMIR_COLLECT_RISK_BLOCK_THRESHOLD", "2")
            ),
            fetched_content_limit=int(
                os.getenv("MIMIR_FETCHED_CONTENT_LIMIT", "10000")
            ),
            cleanup_scan_interval_seconds=float(
                os.getenv("MIMIR_CLEANUP_SCAN_INTERVAL_SECONDS", "60.0")
            ),
        )
