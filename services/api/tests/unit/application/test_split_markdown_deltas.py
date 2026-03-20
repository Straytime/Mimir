"""Unit tests for _split_markdown_deltas helper."""
from app.application.services.delivery import _split_markdown_deltas


def test_empty_string_returns_empty_list() -> None:
    assert _split_markdown_deltas("") == []


def test_short_text_returns_single_chunk() -> None:
    text = "hello world"
    result = _split_markdown_deltas(text, chunk_size=200)
    assert result == ["hello world"]


def test_text_split_into_chunks() -> None:
    text = "a" * 500
    result = _split_markdown_deltas(text, chunk_size=200)
    assert len(result) == 3
    assert result[0] == "a" * 200
    assert result[1] == "a" * 200
    assert result[2] == "a" * 100


def test_exact_chunk_boundary() -> None:
    text = "a" * 400
    result = _split_markdown_deltas(text, chunk_size=200)
    assert len(result) == 2
    assert all(len(chunk) == 200 for chunk in result)


def test_default_chunk_size_is_200() -> None:
    text = "x" * 201
    result = _split_markdown_deltas(text)
    assert len(result) == 2
