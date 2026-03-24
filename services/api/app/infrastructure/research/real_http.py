import json
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

from app.application.dto.invocation import LLMInvocation, PromptBundle
from app.application.dto.research import (
    CollectorDecision,
    CollectorInvocation,
    CollectorToolCall,
    CollectedSourceItem,
    FetchResponse,
    PlannerDecision,
    PlannerInvocation,
    SearchHit,
    SearchResponse,
    SummaryDecision,
    SummaryInvocation,
)
from app.application.services.invocation import (
    OperationTraceSnapshot,
    RetryableOperationError,
    RiskControlTriggered,
    TraceableOperationError,
)
from app.application.services.llm import RetryableLLMError
from app.core.json_utils import (
    extract_first_top_level_json_block,
    strip_markdown_code_fence,
)
from app.domain.enums import CollectSummaryStatus, FreshnessRequirement
from app.domain.schemas import CollectPlan
from app.infrastructure.llm.zhipu import (
    ZhipuChatClient,
    ZhipuClientProtocol,
    ZhipuCompletionResult,
)


def normalize_model_recency_filter(value: str) -> str:
    normalized = value.strip()
    lowered = normalized.lower()
    mapping = {
        "oneday": "oneDay",
        "day": "oneDay",
        "oneweek": "oneWeek",
        "week": "oneWeek",
        "onemonth": "oneMonth",
        "month": "oneMonth",
        "oneyear": "oneYear",
        "year": "oneYear",
        "nolimit": "noLimit",
    }
    if not normalized:
        return "noLimit"
    return mapping.get(lowered, normalized)


def map_recency_filter_to_provider(value: str) -> str:
    return normalize_model_recency_filter(value)


class ZhipuPlannerAgent:
    def __init__(self, *, client: ZhipuChatClient | ZhipuClientProtocol, model: str) -> None:
        self._client = _coerce_chat_client(client)
        self._model = model

    async def plan(self, invocation: PlannerInvocation) -> PlannerDecision:
        if invocation.prompt_bundle is None or invocation.profile is None:
            raise RetryableOperationError("zhipu invocation contract is incomplete")
        try:
            result = await self._client.complete(
                invocation=LLMInvocation(
                    profile=invocation.profile,
                    prompt_bundle=invocation.prompt_bundle,
                    tool_schemas=invocation.tool_schemas,
                )
            )
        except RiskControlTriggered:
            raise
        except RetryableLLMError as exc:
            raise RetryableOperationError("zhipu upstream request failed") from exc

        if result.tool_calls:
            return self._parse_tool_calls(result, invocation)
        if result.text.strip():
            return self._parse_content_json(result, invocation)
        return PlannerDecision(
            reasoning_deltas=(),
            plans=(),
            stop=True,
            request_id=result.request_id,
            provider_finish_reason=result.provider_finish_reason,
            provider_usage=result.provider_usage,
            request_payload=result.request_payload,
            response_payload=result.response_payload,
        )

    def _parse_tool_calls(
        self,
        result: "ZhipuCompletionResult",
        invocation: PlannerInvocation,
    ) -> PlannerDecision:
        plans: list[CollectPlan] = []
        for index, tc in enumerate(result.tool_calls, start=1):
            if tc["name"] != "collect_agent":
                continue
            try:
                args = json.loads(tc["arguments"])
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(args, dict):
                continue
            try:
                freshness_value = str(
                    args.get("freshness_requirement", "high")
                ).lower()
                plans.append(
                    CollectPlan(
                        tool_call_id=tc.get("id") or f"call_plan_{invocation.call_index}_{index}",
                        revision_id="rev_pending",
                        collect_target=str(args["collect_target"]).strip(),
                        additional_info=str(args["additional_info"]).strip(),
                        freshness_requirement=FreshnessRequirement(freshness_value),
                    )
                )
            except (KeyError, ValueError):
                continue
        reasoning_text = (result.reasoning_text or result.text).strip()
        reasoning_deltas = (reasoning_text,) if reasoning_text else ()
        return PlannerDecision(
            reasoning_deltas=reasoning_deltas,
            plans=tuple(plans),
            stop=False,
            request_id=result.request_id,
            provider_finish_reason=result.provider_finish_reason,
            provider_usage=result.provider_usage,
            request_payload=result.request_payload,
            response_payload=result.response_payload,
            tool_calls_json=result.tool_calls,
        )

    @staticmethod
    def _parse_content_json(
        result: "ZhipuCompletionResult",
        invocation: PlannerInvocation,
    ) -> PlannerDecision:
        try:
            parsed = json.loads(strip_markdown_code_fence(result.text))
        except json.JSONDecodeError:
            logger.info(
                "planner returned non-JSON text, treating as stop: request_id=%s",
                result.request_id,
            )
            return PlannerDecision(
                reasoning_deltas=(),
                plans=(),
                stop=True,
                request_id=result.request_id,
                provider_finish_reason=result.provider_finish_reason,
                provider_usage=result.provider_usage,
                request_payload=result.request_payload,
                response_payload=result.response_payload,
            )

        if not isinstance(parsed, dict):
            return PlannerDecision(
                reasoning_deltas=(),
                plans=(),
                stop=True,
                request_id=result.request_id,
                provider_finish_reason=result.provider_finish_reason,
                provider_usage=result.provider_usage,
                request_payload=result.request_payload,
                response_payload=result.response_payload,
            )

        reasoning_deltas = _coerce_string_tuple(parsed.get("reasoning_deltas"))
        if not reasoning_deltas and result.reasoning_text.strip():
            reasoning_deltas = (result.reasoning_text.strip(),)
        stop = bool(parsed.get("stop", False))
        raw_plans = parsed.get("plans") or ()
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
            request_id=result.request_id,
            provider_finish_reason=result.provider_finish_reason,
            provider_usage=result.provider_usage,
            request_payload=result.request_payload,
            response_payload=result.response_payload,
        )


class ZhipuCollectorAgent:
    def __init__(self, *, client: ZhipuChatClient | ZhipuClientProtocol, model: str) -> None:
        self._client = _coerce_chat_client(client)
        self._model = model

    async def plan(self, invocation: CollectorInvocation) -> CollectorDecision:
        if invocation.prompt_bundle is None or invocation.profile is None:
            raise RetryableOperationError("zhipu invocation contract is incomplete")
        try:
            result = await self._client.complete(
                invocation=LLMInvocation(
                    profile=invocation.profile,
                    prompt_bundle=invocation.prompt_bundle,
                    tool_schemas=invocation.tool_schemas,
                )
            )
        except RiskControlTriggered:
            raise
        except RetryableLLMError as exc:
            raise RetryableOperationError("zhipu upstream request failed") from exc

        if result.tool_calls:
            return self._parse_tool_calls(result)
        return self._parse_stop_content(result)

    @staticmethod
    def _parse_tool_calls(result: "ZhipuCompletionResult") -> CollectorDecision:
        tool_calls: list[CollectorToolCall] = []
        for tc in result.tool_calls:
            tool_name = str(tc.get("name") or "").strip()
            if tool_name not in {"web_search", "web_fetch"}:
                continue
            try:
                args = json.loads(tc.get("arguments") or "{}")
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(args, dict):
                continue
            if tool_name == "web_search":
                query = str(args.get("search_query") or "").strip()
                if not query:
                    continue
                arguments_json = {"search_query": query}
                if "search_recency_filter" in args:
                    arguments_json["search_recency_filter"] = normalize_model_recency_filter(
                        str(args.get("search_recency_filter") or "noLimit")
                    )
                else:
                    arguments_json["search_recency_filter"] = "noLimit"
            else:
                url = str(args.get("url") or "").strip()
                if not url:
                    continue
                arguments_json = {"url": url}

            tool_calls.append(
                CollectorToolCall(
                    tool_call_id=str(tc.get("id") or ""),
                    tool_name=tool_name,
                    arguments_json=arguments_json,
                )
            )

        return CollectorDecision(
            reasoning_text=result.reasoning_text.strip(),
            content_text=result.text.strip(),
            tool_calls=tuple(tool_calls),
            stop=False,
            items=(),
            request_id=result.request_id,
            provider_finish_reason=result.provider_finish_reason,
            provider_usage=result.provider_usage,
            request_payload=result.request_payload,
            response_payload=result.response_payload,
        )

    @staticmethod
    def _parse_stop_content(result: "ZhipuCompletionResult") -> CollectorDecision:
        extracted = extract_first_top_level_json_block(result.text)
        if extracted is None:
            logger.error("collector returned invalid JSON response")
            raise TraceableOperationError(
                "zhipu returned invalid JSON",
                trace_snapshot=_build_trace_snapshot(result),
            )
        try:
            parsed = json.loads(extracted)
        except json.JSONDecodeError as exc:
            logger.error("collector returned invalid JSON response", exc_info=True)
            raise TraceableOperationError(
                "zhipu returned invalid JSON",
                trace_snapshot=_build_trace_snapshot(result),
            ) from exc

        if not isinstance(parsed, list):
            raise TraceableOperationError(
                "zhipu returned invalid JSON",
                trace_snapshot=_build_trace_snapshot(result),
            )

        items: list[CollectedSourceItem] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            title = _coerce_optional_string(item.get("title"))
            link = _coerce_optional_string(item.get("link"))
            info = _coerce_optional_string(item.get("info"))
            if not title or not link or not info:
                continue
            items.append(
                CollectedSourceItem(
                    title=title,
                    link=link,
                    info=info,
                )
            )

        return CollectorDecision(
            reasoning_text=result.reasoning_text.strip(),
            content_text=result.text.strip(),
            tool_calls=(),
            stop=True,
            items=tuple(items),
            request_id=result.request_id,
            provider_finish_reason=result.provider_finish_reason,
            provider_usage=result.provider_usage,
            request_payload=result.request_payload,
            response_payload=result.response_payload,
        )


class ZhipuSummaryAgent:
    def __init__(self, *, client: ZhipuChatClient | ZhipuClientProtocol, model: str) -> None:
        self._client = _coerce_chat_client(client)
        self._model = model

    async def summarize(self, invocation: SummaryInvocation) -> SummaryDecision:
        payload, result = await _complete_json(
            client=self._client,
            invocation=invocation,
        )
        return SummaryDecision(
            status=CollectSummaryStatus(str(payload["status"])),
            key_findings_markdown=_coerce_optional_string(
                payload.get("key_findings_markdown")
            ),
            message=_coerce_optional_string(payload.get("message")),
            request_id=result.request_id,
            provider_finish_reason=result.provider_finish_reason,
            provider_usage=result.provider_usage,
            request_payload=result.request_payload,
            response_payload=result.response_payload,
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
        model_filter = normalize_model_recency_filter(recency_filter)
        provider_filter = map_recency_filter_to_provider(model_filter)
        logger.info("web_search starting: query=%s, recency=%s", query, model_filter)
        try:
            response = await self._client.post(
                self._endpoint_path,
                json={
                    "search_engine": self._engine,
                    "query_rewrite": False,
                    "count": 10,
                    "search_query": query,
                    "search_recency_filter": provider_filter,
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
        logger.info("web_search completed: query=%s, results_count=%d", query, len(results))
        return SearchResponse(
            query=query,
            recency_filter=model_filter,
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
    invocation: SummaryInvocation,
) -> tuple[dict[str, Any], ZhipuCompletionResult]:
    if invocation.prompt_bundle is None or invocation.profile is None:
        raise RetryableOperationError("zhipu invocation contract is incomplete")
    prompt_bundle = PromptBundle(
        system_prompt=invocation.prompt_bundle.system_prompt,
        user_prompt=(
            invocation.prompt_bundle.user_prompt
            + "\n\n"
            + _summary_json_instruction()
        ).strip(),
        transcript=invocation.prompt_bundle.transcript,
    )
    logger.info(
        "research _complete_json: prompt_name=%s",
        invocation.prompt_name,
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
        extracted = extract_first_top_level_json_block(result.text)
        if extracted is None:
            logger.error("research _complete_json: invalid JSON response")
            raise TraceableOperationError(
                "zhipu returned invalid JSON",
                trace_snapshot=_build_trace_snapshot(result),
            )
        parsed = json.loads(extracted)
    except json.JSONDecodeError as exc:
        logger.error("research _complete_json: invalid JSON response", exc_info=True)
        raise TraceableOperationError(
            "zhipu returned invalid JSON",
            trace_snapshot=_build_trace_snapshot(result),
        ) from exc

    if not isinstance(parsed, dict):
        raise TraceableOperationError(
            "zhipu returned invalid JSON",
            trace_snapshot=_build_trace_snapshot(result),
        )
    return parsed, result


def _coerce_chat_client(
    client: ZhipuChatClient | ZhipuClientProtocol,
) -> ZhipuChatClient:
    if isinstance(client, ZhipuChatClient):
        return client
    return ZhipuChatClient(client=client)


def _summary_json_instruction() -> str:
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


def _build_trace_snapshot(result: "ZhipuCompletionResult") -> OperationTraceSnapshot:
    return OperationTraceSnapshot(
        parsed_text=result.text,
        reasoning_text=result.reasoning_text.strip(),
        tool_calls_json=tuple(
            dict(tool_call) for tool_call in (result.tool_calls or ())
        ),
        provider_finish_reason=result.provider_finish_reason,
        provider_usage_json=result.provider_usage,
        request_id=result.request_id,
        request_payload=result.request_payload,
        response_payload=result.response_payload,
    )


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
