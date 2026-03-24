import json

from app.core.json_utils import extract_first_top_level_json_block


def test_extract_first_top_level_json_block_returns_object_as_is() -> None:
    payload = {"status": "completed", "message": None}
    text = json.dumps(payload, ensure_ascii=False)

    assert extract_first_top_level_json_block(text) == text


def test_extract_first_top_level_json_block_returns_array_as_is() -> None:
    payload = [{"title": "来源 A", "link": "https://example.com/a", "info": "内容"}]
    text = json.dumps(payload, ensure_ascii=False)

    assert extract_first_top_level_json_block(text) == text


def test_extract_first_top_level_json_block_supports_markdown_code_fence() -> None:
    body = json.dumps({"status": "completed"}, ensure_ascii=False)
    text = f"```json\n{body}\n```"

    assert extract_first_top_level_json_block(text) == body


def test_extract_first_top_level_json_block_extracts_json_with_prefix_and_suffix() -> None:
    body = json.dumps({"status": "completed", "message": "ok"}, ensure_ascii=False)
    text = f"下面是整理结果：\n{body}\n以上是最终输出。"

    assert extract_first_top_level_json_block(text) == body


def test_extract_first_top_level_json_block_returns_none_without_valid_top_level_json() -> None:
    text = "下面是结果：{status: completed，缺少合法 JSON}"

    assert extract_first_top_level_json_block(text) is None
