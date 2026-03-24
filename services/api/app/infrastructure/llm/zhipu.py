import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from app.application.dto.invocation import LLMInvocation
from app.application.services.invocation import RiskControlTriggered
from app.application.services.llm import RetryableLLMError, TextGeneration

logger = logging.getLogger(__name__)


class ChatCompletionsAPI(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class ZhipuClientProtocol(Protocol):
    chat: Any


@dataclass(frozen=True, slots=True)
class ZhipuCompletionResult:
    text: str
    request_id: str | None = None
    reasoning_text: str = ""
    tool_calls: tuple[dict[str, Any], ...] = ()
    provider_finish_reason: str | None = None
    provider_usage: dict[str, Any] | None = None
    request_payload: dict[str, Any] | None = None
    response_payload: dict[str, Any] | None = None


def create_default_zhipu_client(
    *,
    api_key: str,
    base_url: str,
    timeout_seconds: float,
) -> ZhipuClientProtocol:
    try:
        from zai import ZhipuAiClient
    except ImportError:
        try:
            from zai import ZhipuAI as ZhipuAiClient  # type: ignore[attr-defined]
        except ImportError:
            from zhipuai import ZhipuAI as ZhipuAiClient  # type: ignore[import-not-found]

    return ZhipuAiClient(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout_seconds,
    )


class ZhipuChatClient:
    def __init__(
        self,
        *,
        client: ZhipuClientProtocol,
        api_key_hint: str | None = None,
    ) -> None:
        self._client = client
        self._api_key_hint = api_key_hint

    async def complete(
        self,
        *,
        invocation: LLMInvocation,
    ) -> ZhipuCompletionResult:
        messages = [
            message.to_provider_payload()
            for message in invocation.prompt_bundle.messages
        ]
        prompt_chars = sum(
            len(str(m.get("content", ""))) for m in messages
        )
        request_payload = invocation.to_provider_payload()

        logger.info(
            "zhipu LLM call starting: model=%s, messages_count=%d, prompt_chars=%d, thinking=%s, stream=%s",
            invocation.profile.model,
            len(messages),
            prompt_chars,
            invocation.profile.provider_thinking(),
            invocation.profile.stream,
        )
        try:
            response = await asyncio.to_thread(
                self._client.chat.completions.create,
                **request_payload,
            )
        except Exception as exc:  # pragma: no cover - mapped by tests through helpers
            logger.error("zhipu LLM call exception", exc_info=True)
            raise map_zhipu_exception(exc, retryable_cls=RetryableLLMError) from exc

        try:
            if _is_stream_response(response):
                text, diag, tool_calls = await asyncio.to_thread(
                    _extract_stream_with_diagnostics, response
                )
            else:
                text, diag, tool_calls = _extract_response_with_diagnostics(response)
        except Exception as exc:  # pragma: no cover - mapped by tests through helpers
            logger.error("zhipu LLM response extraction exception", exc_info=True)
            raise map_zhipu_exception(exc, retryable_cls=RetryableLLMError) from exc
        request_id = getattr(response, "id", None) or diag.get("request_id")
        if not text.strip() and not tool_calls:
            logger.warning(
                "zhipu LLM returned empty text: request_id=%s, diagnostics=%s",
                request_id,
                diag,
            )
            raise RetryableLLMError("zhipu upstream request failed")
        provider_finish_reason = _normalize_provider_finish_reason(diag)
        provider_usage = _normalize_usage_payload(diag.get("usage_json"))
        response_payload = {
            "request_id": request_id,
            "type": diag.get("type"),
            "provider_finish_reason": provider_finish_reason,
            "provider_usage": provider_usage,
            "parsed_text": text,
            "reasoning_text": str(diag.get("reasoning_text") or ""),
            "tool_calls": list(tool_calls),
            "diagnostics": diag,
        }
        logger.info(
            "zhipu LLM call completed",
            extra={
                "request_id": request_id,
                "provider_finish_reason": provider_finish_reason,
                "provider_usage": provider_usage,
                "response_length": len(text),
                "tool_calls_count": len(tool_calls),
            },
        )
        return ZhipuCompletionResult(
            text=text,
            request_id=request_id,
            reasoning_text=str(diag.get("reasoning_text") or ""),
            tool_calls=tool_calls,
            provider_finish_reason=provider_finish_reason,
            provider_usage=provider_usage,
            request_payload=request_payload,
            response_payload=response_payload,
        )


class _BaseTextGenerator:
    def __init__(
        self,
        *,
        client: ZhipuChatClient | ZhipuClientProtocol,
        api_key_hint: str | None = None,
    ) -> None:
        if isinstance(client, ZhipuChatClient):
            self._client = client
        else:
            self._client = ZhipuChatClient(client=client, api_key_hint=api_key_hint)

    async def _generate(
        self,
        *,
        invocation: LLMInvocation,
    ) -> TextGeneration:
        result = await self._client.complete(invocation=invocation)
        text = result.text.strip()
        return TextGeneration(
            deltas=(text,),
            full_text=text,
            request_id=result.request_id,
            reasoning_text=result.reasoning_text,
            tool_calls=result.tool_calls,
            provider_finish_reason=result.provider_finish_reason,
            provider_usage=result.provider_usage,
            request_payload=result.request_payload,
            response_payload=result.response_payload,
        )


class ZhipuClarificationGenerator(_BaseTextGenerator):
    def __init__(
        self,
        *,
        client: ZhipuChatClient | ZhipuClientProtocol,
        natural_model: str | None = None,
        options_model: str | None = None,
        model: str | None = None,
        api_key_hint: str | None = None,
    ) -> None:
        super().__init__(client=client, api_key_hint=api_key_hint)
        fallback_model = model or "glm-5"
        self._natural_model = natural_model or fallback_model
        self._options_model = options_model or fallback_model

    async def generate_natural(self, invocation: LLMInvocation) -> TextGeneration:
        return await self._generate(invocation=invocation)

    async def generate_options(self, invocation: LLMInvocation) -> TextGeneration:
        return await self._generate(invocation=invocation)


class ZhipuRequirementAnalyzer(_BaseTextGenerator):
    def __init__(
        self,
        *,
        client: ZhipuChatClient | ZhipuClientProtocol,
        model: str,
        api_key_hint: str | None = None,
    ) -> None:
        super().__init__(client=client, api_key_hint=api_key_hint)
        self._model = model

    async def analyze(self, invocation: LLMInvocation) -> TextGeneration:
        return await self._generate(invocation=invocation)


class ZhipuFeedbackAnalyzer(_BaseTextGenerator):
    def __init__(
        self,
        *,
        client: ZhipuChatClient | ZhipuClientProtocol,
        model: str,
        api_key_hint: str | None = None,
    ) -> None:
        super().__init__(client=client, api_key_hint=api_key_hint)
        self._model = model

    async def analyze(self, invocation: LLMInvocation) -> TextGeneration:
        return await self._generate(invocation=invocation)


def extract_response_text(response: Any) -> str:
    text, _, _ = _extract_response_with_diagnostics(response)
    return text


def extract_stream_response_text(response: Iterable[Any]) -> str:
    text, _, _ = _extract_stream_with_diagnostics(response)
    return text


def _extract_response_with_diagnostics(
    response: Any,
) -> tuple[str, dict[str, Any], tuple[dict[str, Any], ...]]:
    diag: dict[str, Any] = {"type": "non_stream"}
    choices = getattr(response, "choices", None)
    if isinstance(response, dict):
        choices = response.get("choices")
    diag["request_id"] = getattr(response, "id", None)
    diag["usage"] = _safe_repr(getattr(response, "usage", None))
    diag["usage_json"] = _normalize_usage_payload(getattr(response, "usage", None))
    if not choices:
        diag["choices_count"] = 0
        diag["raw_response_type"] = type(response).__name__
        return "", diag, ()

    diag["choices_count"] = len(choices)
    choice = choices[0]
    finish_reason = getattr(choice, "finish_reason", None)
    if isinstance(choice, dict):
        finish_reason = choice.get("finish_reason")
    diag["finish_reason"] = finish_reason

    message = getattr(choice, "message", None)
    if isinstance(choice, dict):
        message = choice.get("message")
    content = getattr(message, "content", None)
    if isinstance(message, dict):
        content = message.get("content")
    reasoning = _extract_reasoning_text(message)
    diag["content_type"] = type(content).__name__
    diag["content_repr"] = _safe_repr(content, max_len=500)
    diag["reasoning_text"] = reasoning

    tool_calls = _extract_tool_calls_from_message(message)
    return _coerce_text(content), diag, tool_calls


def _extract_stream_with_diagnostics(
    response: Iterable[Any],
) -> tuple[str, dict[str, Any], tuple[dict[str, Any], ...]]:
    diag: dict[str, Any] = {"type": "stream"}
    parts: list[str] = []
    chunk_count = 0
    no_choices_chunks = 0
    empty_content_chunks = 0
    content_chunks = 0
    finish_reasons: list[str | None] = []
    reasoning_parts: list[str] = []
    last_chunk_repr: str | None = None
    usage: Any = None
    request_id: str | None = None
    tc_builders: dict[int, dict[str, Any]] = {}

    for chunk in response:
        chunk_count += 1
        last_chunk_repr = _safe_repr(chunk, max_len=800)

        cid = getattr(chunk, "id", None)
        if isinstance(chunk, dict):
            cid = chunk.get("id")
        if cid and not request_id:
            request_id = str(cid)

        chunk_usage = getattr(chunk, "usage", None)
        if isinstance(chunk, dict):
            chunk_usage = chunk.get("usage")
        if chunk_usage is not None:
            usage = chunk_usage

        choices = getattr(chunk, "choices", None)
        if isinstance(chunk, dict):
            choices = chunk.get("choices")
        if not choices:
            no_choices_chunks += 1
            continue
        choice = choices[0]

        fr = getattr(choice, "finish_reason", None)
        if isinstance(choice, dict):
            fr = choice.get("finish_reason")
        if fr is not None:
            finish_reasons.append(str(fr))

        delta = getattr(choice, "delta", None)
        if isinstance(choice, dict):
            delta = choice.get("delta")
        reasoning_part = _extract_reasoning_text(delta)
        if reasoning_part:
            reasoning_parts.append(reasoning_part)
        content = getattr(delta, "content", None)
        if isinstance(delta, dict):
            content = delta.get("content")
        part = _coerce_text(content)
        if part:
            parts.append(part)
            content_chunks += 1
        else:
            empty_content_chunks += 1

        _collect_stream_tool_calls(delta, tc_builders)

    tool_calls = _finalize_stream_tool_calls(tc_builders)

    diag["request_id"] = request_id
    diag["chunk_count"] = chunk_count
    diag["no_choices_chunks"] = no_choices_chunks
    diag["empty_content_chunks"] = empty_content_chunks
    diag["content_chunks"] = content_chunks
    diag["finish_reasons"] = finish_reasons
    diag["reasoning_text"] = "".join(reasoning_parts)
    diag["usage"] = _safe_repr(usage)
    diag["usage_json"] = _normalize_usage_payload(usage)
    diag["last_chunk"] = last_chunk_repr
    return "".join(parts), diag, tool_calls


def _normalize_provider_finish_reason(diag: dict[str, Any]) -> str | None:
    finish_reason = diag.get("finish_reason")
    if finish_reason is not None and str(finish_reason).strip():
        return str(finish_reason).strip()
    finish_reasons = diag.get("finish_reasons")
    if isinstance(finish_reasons, list):
        normalized = [str(item).strip() for item in finish_reasons if str(item).strip()]
        if normalized:
            return normalized[-1]
    return None


def _normalize_usage_payload(value: Any) -> dict[str, Any] | None:
    normalized = _normalize_json_value(value)
    if normalized is None:
        return None
    if isinstance(normalized, dict):
        return normalized
    return {"value": normalized}


def _normalize_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            item_value = _normalize_json_value(item)
            if item_value is not None:
                normalized[str(key)] = item_value
        return normalized
    if isinstance(value, (list, tuple)):
        return [_normalize_json_value(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _normalize_json_value(model_dump(mode="json"))
    dump = getattr(value, "dict", None)
    if callable(dump):
        return _normalize_json_value(dump())
    if hasattr(value, "__dict__"):
        return _normalize_json_value(vars(value))
    return repr(value)


def _extract_reasoning_text(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, dict):
        reasoning = (
            payload.get("reasoning_content")
            or payload.get("reasoning")
            or payload.get("thinking")
        )
        return _coerce_text(reasoning)
    reasoning = (
        getattr(payload, "reasoning_content", None)
        or getattr(payload, "reasoning", None)
        or getattr(payload, "thinking", None)
    )
    return _coerce_text(reasoning)


def _extract_tool_calls_from_message(message: Any) -> tuple[dict[str, Any], ...]:
    raw = getattr(message, "tool_calls", None)
    if isinstance(message, dict):
        raw = message.get("tool_calls")
    if not raw:
        return ()
    results: list[dict[str, Any]] = []
    for tc in raw:
        tc_id = getattr(tc, "id", None)
        fn = getattr(tc, "function", None)
        if isinstance(tc, dict):
            tc_id = tc.get("id")
            fn = tc.get("function")
        name = getattr(fn, "name", None)
        arguments = getattr(fn, "arguments", None)
        if isinstance(fn, dict):
            name = fn.get("name")
            arguments = fn.get("arguments")
        if name:
            results.append({"id": tc_id or "", "name": name, "arguments": arguments or ""})
    return tuple(results)


def _collect_stream_tool_calls(
    delta: Any,
    builders: dict[int, dict[str, Any]],
) -> None:
    if delta is None:
        return
    raw = getattr(delta, "tool_calls", None)
    if isinstance(delta, dict):
        raw = delta.get("tool_calls")
    if not raw:
        return
    for tc in raw:
        index = getattr(tc, "index", None)
        if isinstance(tc, dict):
            index = tc.get("index")
        if index is None:
            index = 0
        if index not in builders:
            builders[index] = {"id": "", "name": "", "arguments": ""}
        tc_id = getattr(tc, "id", None)
        if isinstance(tc, dict):
            tc_id = tc.get("id")
        if tc_id:
            builders[index]["id"] = tc_id

        fn = getattr(tc, "function", None)
        if isinstance(tc, dict):
            fn = tc.get("function")
        if fn is not None:
            fn_name = getattr(fn, "name", None)
            fn_args = getattr(fn, "arguments", None)
            if isinstance(fn, dict):
                fn_name = fn.get("name")
                fn_args = fn.get("arguments")
            if fn_name:
                builders[index]["name"] = fn_name
            if fn_args:
                builders[index]["arguments"] += fn_args


def _finalize_stream_tool_calls(
    builders: dict[int, dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    if not builders:
        return ()
    return tuple(builders[i] for i in sorted(builders))


def _safe_repr(obj: Any, *, max_len: int = 300) -> str | None:
    if obj is None:
        return None
    try:
        r = repr(obj)
    except Exception:
        r = f"<{type(obj).__name__}: repr failed>"
    if len(r) > max_len:
        return r[:max_len] + "..."
    return r


def _is_stream_response(response: Any) -> bool:
    return not isinstance(response, (dict, str, bytes)) and hasattr(response, "__iter__")


def _coerce_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
                continue
            parts.append(str(getattr(item, "text", "") or getattr(item, "content", "")))
        return "".join(part for part in parts if part)
    if isinstance(content, dict):
        return str(content.get("text") or content.get("content") or "")
    return str(content or "")


def map_zhipu_exception(
    exc: Exception,
    *,
    retryable_cls: type[Exception],
) -> Exception:
    if is_risk_control_error(exc):
        return RiskControlTriggered("zhipu risk control triggered")
    return retryable_cls("zhipu upstream request failed")


def is_risk_control_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code not in {400, "400"}:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
        if status_code not in {400, "400"}:
            return False

    body = getattr(exc, "body", None)
    if body is None:
        response = getattr(exc, "response", None)
        if response is not None:
            json_method = getattr(response, "json", None)
            if callable(json_method):
                try:
                    body = json_method()
                except Exception:  # pragma: no cover - defensive
                    body = None
    return extract_error_code(body) == "1301"


def extract_error_code(payload: Any) -> str | None:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and "code" in error:
            return str(error["code"])
        if "code" in payload:
            return str(payload["code"])
    return None
