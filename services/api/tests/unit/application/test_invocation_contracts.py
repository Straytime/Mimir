from app.application.invocation_contracts import (
    build_collect_agent_tool_schema,
    build_python_interpreter_tool_schema,
    build_stage_profile,
    build_web_fetch_tool_schema,
    build_web_search_tool_schema,
)
from app.core.config import Settings


def test_stage_profiles_match_architecture_defaults() -> None:
    settings = Settings()

    clarification_natural = build_stage_profile(
        settings=settings,
        stage="clarification_natural",
    )
    assert clarification_natural.model == "glm-5"
    assert clarification_natural.temperature == 0.5
    assert clarification_natural.top_p == 0.8
    assert clarification_natural.max_tokens == 98304
    assert clarification_natural.thinking is False
    assert clarification_natural.clear_thinking is None
    assert clarification_natural.stream is True

    planner = build_stage_profile(settings=settings, stage="planner")
    assert planner.model == "glm-5"
    assert planner.temperature == 1
    assert planner.top_p == 1
    assert planner.max_tokens == 98304
    assert planner.thinking is True
    assert planner.clear_thinking is False
    assert planner.stream is True

    collector = build_stage_profile(settings=settings, stage="collector")
    assert collector.model == "glm-5"
    assert collector.temperature == 1
    assert collector.top_p == 1
    assert collector.max_tokens == 98304
    assert collector.thinking is True
    assert collector.clear_thinking is False
    assert collector.stream is True

    summary = build_stage_profile(settings=settings, stage="summary")
    assert summary.model == "glm-5"
    assert summary.temperature == 0.6
    assert summary.top_p == 0.8
    assert summary.max_tokens == 98304
    assert summary.thinking is False
    assert summary.clear_thinking is None
    assert summary.stream is True

    writer = build_stage_profile(settings=settings, stage="writer")
    assert writer.model == "glm-5"
    assert writer.temperature == 1
    assert writer.top_p == 1
    assert writer.max_tokens == 98304
    assert writer.thinking is True
    assert writer.clear_thinking is False
    assert writer.stream is True

    outline = build_stage_profile(settings=settings, stage="outline")
    assert outline.model == "glm-5"
    assert outline.temperature == 1
    assert outline.top_p == 1
    assert outline.max_tokens == 98304
    assert outline.thinking is True
    assert outline.clear_thinking is False
    assert outline.stream is True


def test_tool_schemas_match_current_architecture_contract() -> None:
    collect_agent = build_collect_agent_tool_schema()
    assert collect_agent.name == "collect_agent"
    assert set(collect_agent.parameters) == {
        "collect_target",
        "additional_info",
        "freshness_requirement",
    }
    assert "tool_call_id" not in collect_agent.parameters
    assert "revision_id" not in collect_agent.parameters
    assert "subtask_id" not in collect_agent.parameters

    web_search = build_web_search_tool_schema()
    assert web_search.name == "web_search"
    assert set(web_search.parameters) == {
        "search_query",
        "search_recency_filter",
    }
    assert web_search.parameters["search_recency_filter"]["enum"] == [
        "oneDay",
        "oneWeek",
        "oneMonth",
        "oneYear",
        "noLimit",
    ]

    web_fetch = build_web_fetch_tool_schema()
    assert web_fetch.name == "web_fetch"
    assert set(web_fetch.parameters) == {"url"}

    python_interpreter = build_python_interpreter_tool_schema()
    assert python_interpreter.name == "python_interpreter"
    assert set(python_interpreter.parameters) == {"code"}
