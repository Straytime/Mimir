from app.application.dto.research import (
    SearchHit,
    SearchResponse,
    build_web_search_tool_payload,
)


def test_build_web_search_tool_payload_keeps_publish_date_and_core_fields() -> None:
    payload = build_web_search_tool_payload(
        SearchResponse(
            query="中国 AI 搜索",
            recency_filter="oneWeek",
            results=(
                SearchHit(
                    title="来源 A",
                    link="https://example.com/a",
                    snippet="摘要 A",
                    publish_date="2025-06-10",
                ),
            ),
        )
    )

    assert payload == {
        "success": True,
        "search_query": "中国 AI 搜索",
        "search_recency_filter": "oneWeek",
        "results": [
            {
                "title": "来源 A",
                "link": "https://example.com/a",
                "snippet": "摘要 A",
                "publish_date": "2025-06-10",
            }
        ],
    }


def test_build_web_search_tool_payload_uses_null_for_missing_publish_date() -> None:
    payload = build_web_search_tool_payload(
        SearchResponse(
            query="中国 AI 搜索",
            recency_filter="noLimit",
            results=(
                SearchHit(
                    title="来源 A",
                    link="https://example.com/a",
                    snippet="摘要 A",
                ),
            ),
        )
    )

    assert payload["results"] == [
        {
            "title": "来源 A",
            "link": "https://example.com/a",
            "snippet": "摘要 A",
            "publish_date": None,
        }
    ]


def test_build_web_search_tool_payload_keeps_shape_on_failure() -> None:
    payload = build_web_search_tool_payload(
        None,
        search_query="中国 AI 搜索",
        search_recency_filter="oneDay",
        error_code="retry_exhausted",
    )

    assert payload == {
        "success": False,
        "search_query": "中国 AI 搜索",
        "search_recency_filter": "oneDay",
        "results": [],
        "error_code": "retry_exhausted",
    }
