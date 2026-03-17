from dataclasses import replace

import pytest

from app.core.config import Settings
from app.infrastructure.delivery.local import LocalStubOutlineAgent, LocalStubWriterAgent
from app.infrastructure.delivery.zhipu import ZhipuOutlineAgent, ZhipuWriterAgent
from app.infrastructure.llm.local_stub import (
    LocalStubClarificationGenerator,
    LocalStubFeedbackAnalyzer,
    LocalStubRequirementAnalyzer,
)
from app.infrastructure.llm.zhipu import (
    ZhipuClarificationGenerator,
    ZhipuFeedbackAnalyzer,
    ZhipuRequirementAnalyzer,
)
from app.infrastructure.providers import build_provider_runtime
from app.infrastructure.research.local_stub import (
    LocalStubCollectorAgent,
    LocalStubPlannerAgent,
    LocalStubSummaryAgent,
    LocalStubWebFetchClient,
    LocalStubWebSearchClient,
)
from app.infrastructure.research.real_http import (
    HttpWebFetchClient,
    ZhipuCollectorAgent,
    ZhipuPlannerAgent,
    ZhipuSummaryAgent,
    ZhipuWebSearchClient,
)


def test_build_provider_runtime_uses_stub_adapters_when_provider_mode_is_stub() -> None:
    runtime = build_provider_runtime(Settings())

    assert isinstance(runtime.clarification_generator, LocalStubClarificationGenerator)
    assert isinstance(runtime.requirement_analyzer, LocalStubRequirementAnalyzer)
    assert isinstance(runtime.feedback_analyzer, LocalStubFeedbackAnalyzer)
    assert isinstance(runtime.planner_agent, LocalStubPlannerAgent)
    assert isinstance(runtime.collector_agent, LocalStubCollectorAgent)
    assert isinstance(runtime.summary_agent, LocalStubSummaryAgent)
    assert isinstance(runtime.web_search_client, LocalStubWebSearchClient)
    assert isinstance(runtime.web_fetch_client, LocalStubWebFetchClient)
    assert isinstance(runtime.outline_agent, LocalStubOutlineAgent)
    assert isinstance(runtime.writer_agent, LocalStubWriterAgent)


def test_build_provider_runtime_uses_real_adapters_when_provider_mode_is_real() -> None:
    runtime = build_provider_runtime(
        replace(
            Settings(),
            provider_mode="real",
            zhipu_api_key="secret-key",
        )
    )

    assert isinstance(runtime.clarification_generator, ZhipuClarificationGenerator)
    assert isinstance(runtime.requirement_analyzer, ZhipuRequirementAnalyzer)
    assert isinstance(runtime.feedback_analyzer, ZhipuFeedbackAnalyzer)
    assert isinstance(runtime.planner_agent, ZhipuPlannerAgent)
    assert isinstance(runtime.collector_agent, ZhipuCollectorAgent)
    assert isinstance(runtime.summary_agent, ZhipuSummaryAgent)
    assert isinstance(runtime.web_search_client, ZhipuWebSearchClient)
    assert isinstance(runtime.web_fetch_client, HttpWebFetchClient)
    assert isinstance(runtime.outline_agent, ZhipuOutlineAgent)
    assert isinstance(runtime.writer_agent, ZhipuWriterAgent)


def test_settings_from_env_fails_fast_when_real_provider_mode_lacks_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MIMIR_PROVIDER_MODE", "real")
    monkeypatch.delenv("MIMIR_ZHIPU_API_KEY", raising=False)
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)

    with pytest.raises(
        ValueError,
        match="ZHIPU_API_KEY",
    ):
        Settings.from_env()
