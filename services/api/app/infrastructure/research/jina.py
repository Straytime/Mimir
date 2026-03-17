"""Jina Reader web_fetch adapter.

Uses https://r.jina.ai/<url> to fetch and convert web pages to plain text / markdown.
"""

import re

import httpx

from app.application.dto.research import FetchResponse
from app.application.services.invocation import RetryableOperationError

_DEFAULT_BASE_URL = "https://r.jina.ai/"
_MAX_FETCH_CONTENT_CHARS = 10000


class JinaWebFetchClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/") + "/"
        self._client = httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "text/plain",
            },
            transport=transport,
        )

    async def fetch(self, url: str) -> FetchResponse:
        reader_url = f"{self._base_url}{url}"
        try:
            response = await self._client.get(reader_url)
        except httpx.HTTPError:
            raise RetryableOperationError("web_fetch upstream request failed")

        if response.status_code >= 500:
            raise RetryableOperationError("web_fetch upstream request failed")
        if response.status_code >= 400:
            return FetchResponse(url=url, success=False, title=None, content=None)

        body = response.text.strip()
        if not body:
            return FetchResponse(url=url, success=False, title=None, content=None)

        title = _extract_title(body, fallback=url)
        return FetchResponse(
            url=url,
            success=True,
            title=title,
            content=body[:_MAX_FETCH_CONTENT_CHARS],
        )

    async def aclose(self) -> None:
        await self._client.aclose()


def _extract_title(body: str, *, fallback: str) -> str:
    first_line = body.splitlines()[0].strip()
    match = re.match(r"^#+\s+(.*)", first_line)
    if match:
        return match.group(1).strip()
    return first_line[:120] or fallback
