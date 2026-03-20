import hashlib

import pytest

from app.infrastructure.db.repositories import _source_key


class TestSourceKey:
    def test_normal_url_returns_64_char_hex_digest(self) -> None:
        result = _source_key("https://example.com/article-1")
        assert len(result) == 64
        expected = hashlib.sha256("https://example.com/article-1".encode()).hexdigest()
        assert result == expected

    def test_long_url_over_1000_chars_returns_64_char_hex_digest(self) -> None:
        long_url = "https://example.com/" + "x" * 2000
        result = _source_key(long_url)
        assert len(result) == 64
        expected = hashlib.sha256(long_url.encode()).hexdigest()
        assert result == expected

    def test_empty_string_returns_64_char_hex_digest(self) -> None:
        result = _source_key("")
        assert len(result) == 64
        expected = hashlib.sha256(b"").hexdigest()
        assert result == expected

    def test_strips_whitespace_and_lowercases_before_hashing(self) -> None:
        result = _source_key("  HTTPS://Example.COM/Path  ")
        expected = hashlib.sha256("https://example.com/path".encode()).hexdigest()
        assert result == expected

    def test_same_url_always_produces_same_hash(self) -> None:
        url = "https://example.com/stable"
        assert _source_key(url) == _source_key(url)

    def test_different_urls_produce_different_hashes(self) -> None:
        assert _source_key("https://a.com") != _source_key("https://b.com")
