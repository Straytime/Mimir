import json
import re
from typing import Any

import httpx

from app.application.dto.invocation import LLMInvocation, PromptBundle
from app.application.dto.research import (
    CollectorDecision,
    CollectorInvocation,
    FetchResponse,
    PlannerDecision,
    PlannerInvocation,
    SearchHit,
    SearchResponse,
    SummaryDecision,
    SummaryInvocation,
)
from app.application.services.invocation import (
    RetryableOperationError,
    RiskControlTriggered,
)
from app.application.services.llm import RetryableLLMError
from app.core.json_utils import strip_markdown_code_fence
from app.domain.enums import CollectSummaryStatus, FreshnessRequirement
from app.domain.schemas import CollectPlan
from app.infrastructure.llm.zhipu import (
    ZhipuChatClient,
    ZhipuClientProtocol,
)


def normalize_recency_filter(value: str) -> str:
    return "noLimit" if value.strip().lower() == "nolimit" else value


class ZhipuPlannerAgent:
    def __init__(self, *, client: ZhipuChatClient | ZhipuClientProtocol, model: str) -> None:
        self._client = _coerce_chat_client(client)
        self._model = model

    async def plan(self, invocation: PlannerInvocation) -> PlannerDecision:
        payload = await _complete_json(
            client=self._client,
            invocation=invocation,
        )
        reasoning_deltas = _coerce_string_tuple(payload.get("reasoning_deltas"))
        stop = bool(payload.get("stop", False))
        raw_plans = payload.get("plans") or ()
        plans: list[CollectPlan] = []
        for index, item in enumerate(raw_plans, start=1):
            if not isinstance(item, dict):
                continue
            try:
                freshness_value = str(
                    item.get("freshness_requirement", "high")
                ).lower()
                plans.append(
                    CollectPlan(
                        tool_call_id=str(
                            item.get("tool_call_id")
                            or f"call_plan_{invocation.call_index}_{index}"
                        ),
                        revision_id=str(item.get("revision_id") or "rev_pending"),
                        collect_target=str(item["collect_target"]).strip(),
                        additional_info=str(item["additional_info"]).strip(),
                        freshness_requirement=FreshnessRequirement(freshness_value),
                    )
                )
            except (KeyError, ValueError):
                continue
        return PlannerDecision(
            reasoning_deltas=reasoning_deltas,
            plans=tuple(plans),
            stop=stop,
        )


class ZhipuCollectorAgent:
    def __init__(self, *, client: ZhipuChatClient | ZhipuClientProtocol, model: str) -> None:
        self._client = _coerce_chat_client(client)
        self._model = model

    async def plan(self, invocation: CollectorInvocation) -> CollectorDecision:
        payload = await _complete_json(
            client=self._client,
            invocation=invocation,
        )
        return CollectorDecision(
            reasoning_deltas=_coerce_string_tuple(payload.get("reasoning_deltas")),
            search_queries=_coerce_string_tuple(payload.get("search_queries")),
            search_recency_filter=normalize_recency_filter(
                str(payload.get("search_recency_filter", "noLimit"))
            ),
        )


class ZhipuSummaryAgent:
    def __init__(self, *, client: ZhipuChatClient | ZhipuClientProtocol, model: str) -> None:
        self._client = _coerce_chat_client(client)
        self._model = model

    async def summarize(self, invocation: SummaryInvocation) -> SummaryDecision:
        payload = await _complete_json(
            client=self._client,
            invocation=invocation,
        )
        return SummaryDecision(
            status=CollectSummaryStatus(str(payload["status"])),
            key_findings_markdown=_coerce_optional_string(
                payload.get("key_findings_markdown")
            ),
            message=_coerce_optional_string(payload.get("message")),
        )


class ZhipuWebSearchClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        endpoint_path: str = "web_search",
        engine: str = "search_prime",
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._engine = engine
        self._endpoint_path = endpoint_path.lstrip("/")
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    async def search(self, query: str, recency_filter: str) -> SearchResponse:
        normalized_filter = normalize_recency_filter(recency_filter)
        try:
            response = await self._client.post(
                self._endpoint_path,
                json={
                    "search_engine": self._engine,
                    "query_rewrite": False,
                    "count": 10,
                    "search_query": query,
                    "search_recency_filter": normalized_filter,
                },
            )
        except httpx.HTTPError as exc:
            raise RetryableOperationError("web_search upstream request failed") from exc

        payload = _read_json(response)
        if response.status_code == 400 and _extract_error_code(payload) == "1301":
            raise RiskControlTriggered("web_search risk control triggered")
        if response.status_code >= 400:
            raise RetryableOperationError("web_search upstream request failed")

        raw_results = _find_search_results(payload)
        results: list[SearchHit] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            title = _coerce_optional_string(item.get("title"))
            link = _coerce_optional_string(item.get("link") or item.get("url"))
            snippet = _coerce_optional_string(
                item.get("snippet") or item.get("content") or item.get("summary")
            )
            if not title or not link:
                continue
            results.append(
                SearchHit(
                    title=title,
                    link=link,
                    snippet=snippet or "",
                )
            )

        if not results:
            raise RetryableOperationError("web_search returned invalid response")
        return SearchResponse(
            query=query,
            recency_filter=normalized_filter,
            results=tuple(results),
        )

    async def aclose(self) -> None:
        await self._client.aclose()


class HttpWebFetchClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        user_agent: str = "mimir-api/0.1",
        transport: httpx.BaseTransport | httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": user_agent},
            transport=transport,
        )

    async def fetch(self, url: str) -> FetchResponse:
        try:
            response = await self._client.get(url)
        except httpx.HTTPError as exc:
            raise RetryableOperationError("web_fetch upstream request failed") from exc

        if response.status_code >= 500:
            raise RetryableOperationError("web_fetch upstream request failed")
        if response.status_code >= 400:
            return FetchResponse(url=url, success=False, title=None, content=None)

        content_type = response.headers.get("content-type", "").lower()
        if not _is_textual_content_type(content_type):
            return FetchResponse(url=url, success=False, title=None, content=None)

        body = response.text.strip()
        if not body:
            return FetchResponse(url=url, success=False, title=None, content=None)

        title = _extract_title(body, fallback=url)
        content = _extract_text_content(body, content_type)
        if not content:
            return FetchResponse(url=url, success=False, title=title, content=None)
        return FetchResponse(
            url=url,
            success=True,
            title=title,
            content=content,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

async def _complete_json(
    *,
    client: ZhipuChatClient,
    invocation: PlannerInvocation | CollectorInvocation | SummaryInvocation,
) -> dict[str, Any]:
    if invocation.prompt_bundle is None or invocation.profile is None:
        raise RetryableOperationError("zhipu invocation contract is incomplete")
    prompt_bundle = PromptBundle(
        system_prompt=invocation.prompt_bundle.system_prompt,
        user_prompt=(
            invocation.prompt_bundle.user_prompt
            + "\n\n"
            + _json_instruction_for_invocation(invocation)
        ).strip(),
        transcript=invocation.prompt_bundle.transcript,
    )
    try:
        result = await client.complete(
            invocation=LLMInvocation(
                profile=invocation.profile,
                prompt_bundle=prompt_bundle,
                tool_schemas=invocation.tool_schemas,
            )
        )
    except RiskControlTriggered:
        raise
    except RetryableLLMError as exc:
        raise RetryableOperationError("zhipu upstream request failed") from exc

    try:
        parsed = json.loads(strip_markdown_code_fence(result.text))
    except json.JSONDecodeError as exc:
        raise RetryableOperationError("zhipu returned invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise RetryableOperationError("zhipu returned invalid JSON")
    return parsed


def _coerce_chat_client(
    client: ZhipuChatClient | ZhipuClientProtocol,
) -> ZhipuChatClient:
    if isinstance(client, ZhipuChatClient):
        return client
    return ZhipuChatClient(client=client)


def _json_instruction_for_invocation(
    invocation: PlannerInvocation | CollectorInvocation | SummaryInvocation,
) -> str:
    if isinstance(invocation, PlannerInvocation):
        return (
            '请输出合法 JSON：{"reasoning_deltas": string[], "stop": boolean, '
            '"plans": [{"collect_target": string, "additional_info": string, '
            '"freshness_requirement": "low|high"}]}。不要输出 Markdown 代码块，不要输出额外解释。'
        )
    if isinstance(invocation, CollectorInvocation):
        return (
            '请输出合法 JSON：{"reasoning_deltas": string[], "search_queries": string[], '
            '"search_recency_filter": "day|week|month|year|noLimit"}。'
            "不要输出 Markdown 代码块，不要输出额外解释。"
        )
    return (
        '请输出合法 JSON：{"status": "completed|partial|risk_blocked", '
        '"key_findings_markdown": string|null, "message": string|null}。'
        "不要输出 Markdown 代码块，不要输出额外解释。"
    )


def _coerce_string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        cleaned = value.strip()
        return (cleaned,) if cleaned else ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def _coerce_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _read_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise RetryableOperationError("upstream returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RetryableOperationError("upstream returned invalid JSON")
    return payload


def _extract_error_code(payload: dict[str, Any]) -> str | None:
    error = payload.get("error")
    if isinstance(error, dict) and "code" in error:
        return str(error["code"])
    if "code" in payload:
        return str(payload["code"])
    return None


def _find_search_results(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    for key in ("search_result", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return tuple(item for item in value if isinstance(item, dict))
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("search_result", "results"):
            value = data.get(key)
            if isinstance(value, list):
                return tuple(item for item in value if isinstance(item, dict))
    return ()


def _is_textual_content_type(content_type: str) -> bool:
    return (
        "text/" in content_type
        or "application/json" in content_type
        or "application/xml" in content_type
        or "application/xhtml+xml" in content_type
    )


def _extract_title(body: str, *, fallback: str) -> str:
    match = re.search(r"<title>(.*?)</title>", body, flags=re.IGNORECASE | re.DOTALL)
    if match is not None:
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        if title:
            return title
    first_line = body.splitlines()[0].strip()
    return first_line[:120] or fallback


def _extract_text_content(body: str, content_type: str) -> str:
    if "html" not in content_type and "<html" not in body.lower():
        return body
    cleaned = re.sub(
        r"<(script|style).*?>.*?</\1>",
        " ",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
