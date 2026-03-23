"""Jina Reader web_fetch adapter.

Uses https://r.jina.ai/<url> to fetch and convert web pages to plain text / markdown.
"""

import logging
import re

import httpx

from app.application.dto.research import FetchResponse
from app.application.services.invocation import RetryableOperationError

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://r.jina.ai/"
_DEFAULT_MAX_FETCH_CONTENT_CHARS = 5000


class JinaWebFetchClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 30.0,
        max_content_chars: int = _DEFAULT_MAX_FETCH_CONTENT_CHARS,
        transport: httpx.BaseTransport | httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/") + "/"
        self._max_content_chars = max_content_chars
        headers: dict[str, str] = {"Accept": "text/plain"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.AsyncClient(
            timeout=timeout_seconds,
            headers=headers,
            transport=transport,
        )

    async def fetch(self, url: str) -> FetchResponse:
        reader_url = f"{self._base_url}{url}"
        logger.info("jina web_fetch starting: url=%s", url)
        try:
            response = await self._client.get(reader_url)
        except httpx.HTTPError:
            logger.error("jina web_fetch request failed: url=%s", url, exc_info=True)
            raise RetryableOperationError("web_fetch upstream request failed")

        if response.status_code >= 500:
            raise RetryableOperationError("web_fetch upstream request failed")
        if response.status_code >= 400:
            return FetchResponse(url=url, success=False, title=None, content=None)

        body = response.text.strip()
        if not body:
            return FetchResponse(url=url, success=False, title=None, content=None)

        title = _extract_title(body, fallback=url)
        logger.info("jina web_fetch completed: url=%s, status=%d, content_length=%d", url, response.status_code, len(body))
        return FetchResponse(
            url=url,
            success=True,
            title=title,
            content=body[: self._max_content_chars],
        )

    async def aclose(self) -> None:
        await self._client.aclose()


def _extract_title(body: str, *, fallback: str) -> str:
    first_line = body.splitlines()[0].strip()
    match = re.match(r"^#+\s+(.*)", first_line)
    if match:
        return match.group(1).strip()
    return first_line[:120] or fallback
