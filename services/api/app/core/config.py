from dataclasses import dataclass
import os

from app.core.database_url import resolve_database_url_from_env

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
    provider_mode: str = "stub"
    llm_provider_mode: str | None = None
    web_search_provider_mode: str | None = None
    web_fetch_provider_mode: str | None = None
    e2b_provider_mode: str | None = None
    artifact_root_dir: str | None = None
    jina_api_key: str | None = None
    jina_base_url: str = "https://r.jina.ai/"
    zhipu_api_key: str | None = None
    e2b_api_key: str | None = None
    e2b_request_timeout_seconds: float = 30.0
    e2b_execution_timeout_seconds: float = 120.0
    e2b_sandbox_timeout_seconds: int = 600
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    zhipu_timeout_seconds: float = 30.0
    zhipu_clarification_natural_model: str = "glm-5"
    zhipu_clarification_options_model: str = "glm-5"
    zhipu_requirement_analyzer_model: str = "glm-5"
    zhipu_feedback_analyzer_model: str = "glm-5"
    zhipu_planner_model: str = "glm-5"
    zhipu_collector_model: str = "glm-5"
    zhipu_summary_model: str = "glm-5"
    zhipu_outline_model: str = "glm-5"
    zhipu_writer_model: str = "glm-5"
    web_search_endpoint_path: str = "web_search"
    web_search_engine: str = "search_prime"
    web_search_timeout_seconds: float = 30.0
    web_fetch_timeout_seconds: float = 30.0
    web_fetch_user_agent: str = "mimir-api/0.1 (+https://github.com/Straytime/Mimir)"
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
        settings = cls(
            service_name=os.getenv("MIMIR_SERVICE_NAME", "mimir-api"),
            service_version=os.getenv("MIMIR_SERVICE_VERSION", "v1"),
            database_url=resolve_database_url_from_env(),
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
            provider_mode=os.getenv("MIMIR_PROVIDER_MODE", "stub"),
            llm_provider_mode=os.getenv("MIMIR_LLM_PROVIDER_MODE"),
            web_search_provider_mode=os.getenv("MIMIR_WEB_SEARCH_PROVIDER_MODE"),
            web_fetch_provider_mode=os.getenv("MIMIR_WEB_FETCH_PROVIDER_MODE"),
            e2b_provider_mode=os.getenv("MIMIR_E2B_PROVIDER_MODE"),
            artifact_root_dir=_resolve_artifact_root_dir(),
            jina_api_key=os.getenv("MIMIR_JINA_API_KEY") or os.getenv("JINA_API_KEY"),
            jina_base_url=os.getenv(
                "MIMIR_JINA_BASE_URL",
                "https://r.jina.ai/",
            ),
            zhipu_api_key=os.getenv("MIMIR_ZHIPU_API_KEY") or os.getenv("ZHIPU_API_KEY"),
            e2b_api_key=os.getenv("MIMIR_E2B_API_KEY") or os.getenv("E2B_API_KEY"),
            e2b_request_timeout_seconds=float(
                os.getenv("MIMIR_E2B_REQUEST_TIMEOUT_SECONDS", "30")
            ),
            e2b_execution_timeout_seconds=float(
                os.getenv("MIMIR_E2B_EXECUTION_TIMEOUT_SECONDS", "120")
            ),
            e2b_sandbox_timeout_seconds=int(
                os.getenv("MIMIR_E2B_SANDBOX_TIMEOUT_SECONDS", "600")
            ),
            zhipu_base_url=os.getenv(
                "MIMIR_ZHIPU_BASE_URL",
                "https://open.bigmodel.cn/api/paas/v4/",
            ),
            zhipu_timeout_seconds=float(
                os.getenv("MIMIR_ZHIPU_TIMEOUT_SECONDS", "30")
            ),
            zhipu_clarification_natural_model=os.getenv(
                "MIMIR_ZHIPU_MODEL_CLARIFICATION_NATURAL",
                "glm-5",
            ),
            zhipu_clarification_options_model=os.getenv(
                "MIMIR_ZHIPU_MODEL_CLARIFICATION_OPTIONS",
                "glm-5",
            ),
            zhipu_requirement_analyzer_model=os.getenv(
                "MIMIR_ZHIPU_MODEL_REQUIREMENT_ANALYZER",
                "glm-5",
            ),
            zhipu_feedback_analyzer_model=os.getenv(
                "MIMIR_ZHIPU_MODEL_FEEDBACK_ANALYZER",
                "glm-5",
            ),
            zhipu_planner_model=os.getenv(
                "MIMIR_ZHIPU_MODEL_PLANNER",
                "glm-5",
            ),
            zhipu_collector_model=os.getenv(
                "MIMIR_ZHIPU_MODEL_COLLECTOR",
                "glm-5",
            ),
            zhipu_summary_model=os.getenv(
                "MIMIR_ZHIPU_MODEL_SUMMARIZER",
                "glm-5",
            ),
            zhipu_outline_model=os.getenv(
                "MIMIR_ZHIPU_MODEL_OUTLINER",
                "glm-5",
            ),
            zhipu_writer_model=os.getenv(
                "MIMIR_ZHIPU_MODEL_WRITER",
                "glm-5",
            ),
            web_search_endpoint_path=os.getenv(
                "MIMIR_WEB_SEARCH_ENDPOINT_PATH",
                "web_search",
            ),
            web_search_engine=os.getenv(
                "MIMIR_WEB_SEARCH_ENGINE",
                "search_prime",
            ),
            web_search_timeout_seconds=float(
                os.getenv("MIMIR_WEB_SEARCH_TIMEOUT_SECONDS", "30")
            ),
            web_fetch_timeout_seconds=float(
                os.getenv("MIMIR_WEB_FETCH_TIMEOUT_SECONDS", "30")
            ),
            web_fetch_user_agent=os.getenv(
                "MIMIR_WEB_FETCH_USER_AGENT",
                "mimir-api/0.1 (+https://github.com/Straytime/Mimir)",
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
        settings.validate_provider_configuration()
        return settings

    def resolved_llm_provider_mode(self) -> str:
        return _resolve_provider_mode(self.llm_provider_mode or self.provider_mode)

    def resolved_web_search_provider_mode(self) -> str:
        return _resolve_provider_mode(
            self.web_search_provider_mode or self.provider_mode
        )

    def resolved_web_fetch_provider_mode(self) -> str:
        return _resolve_provider_mode(
            self.web_fetch_provider_mode or self.provider_mode
        )

    def resolved_e2b_provider_mode(self) -> str:
        return _resolve_provider_mode(
            self.e2b_provider_mode or self.provider_mode
        )

    def validate_provider_configuration(self) -> None:
        if (
            self.resolved_llm_provider_mode() == "real"
            or self.resolved_web_search_provider_mode() == "real"
        ) and not self.zhipu_api_key:
            raise ValueError(
                "ZHIPU_API_KEY (or MIMIR_ZHIPU_API_KEY) is required when real providers are enabled."
            )
        # JINA_API_KEY is optional: when empty, JinaWebFetchClient runs in
        # free unauthenticated mode (lower RPM limit but no token needed).
        if self.resolved_e2b_provider_mode() == "real" and not self.e2b_api_key:
            raise ValueError(
                "E2B_API_KEY (or MIMIR_E2B_API_KEY) is required when real E2B provider is enabled."
            )


def _resolve_provider_mode(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"stub", "real"}:
        raise ValueError(
            "Provider mode must be either 'stub' or 'real'."
        )
    return normalized


def _resolve_artifact_root_dir() -> str | None:
    configured = os.getenv("MIMIR_ARTIFACT_ROOT_DIR")
    if configured:
        return configured

    railway_mount_path = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    if railway_mount_path:
        return os.path.join(railway_mount_path, "mimir-artifacts")

    return None
