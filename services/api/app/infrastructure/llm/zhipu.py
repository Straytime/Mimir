import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

from app.application.services.invocation import RiskControlTriggered
from app.application.services.llm import RetryableLLMError, TextGeneration


class ChatCompletionsAPI(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class ZhipuClientProtocol(Protocol):
    chat: Any


@dataclass(frozen=True, slots=True)
class ZhipuCompletionResult:
    text: str
    request_id: str | None = None


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
        model: str,
        prompt: str,
        system_prompt: str | None = None,
    ) -> ZhipuCompletionResult:
        messages: list[dict[str, str]] = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await asyncio.to_thread(
                self._client.chat.completions.create,
                model=model,
                messages=messages,
            )
        except Exception as exc:  # pragma: no cover - mapped by tests through helpers
            raise map_zhipu_exception(exc, retryable_cls=RetryableLLMError) from exc

        text = extract_response_text(response)
        if not text.strip():
            raise RetryableLLMError("zhipu upstream request failed")
        return ZhipuCompletionResult(
            text=text,
            request_id=getattr(response, "id", None),
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
        model: str,
        prompt: str,
        system_prompt: str | None = None,
    ) -> TextGeneration:
        result = await self._client.complete(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
        )
        text = result.text.strip()
        return TextGeneration(
            deltas=(text,),
            full_text=text,
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
        fallback_model = model or "glm-4.7"
        self._natural_model = natural_model or fallback_model
        self._options_model = options_model or fallback_model

    async def generate_natural(self, prompt: str) -> TextGeneration:
        return await self._generate(
            model=self._natural_model,
            prompt=prompt,
            system_prompt="你是 Mimir 的自然语言澄清生成器，只输出用户可见问题正文。",
        )

    async def generate_options(self, prompt: str) -> TextGeneration:
        return await self._generate(
            model=self._options_model,
            prompt=prompt,
            system_prompt="你是 Mimir 的选项澄清生成器，只输出问题与选项正文。",
        )


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

    async def analyze(self, prompt: str) -> TextGeneration:
        return await self._generate(
            model=self._model,
            prompt=prompt,
            system_prompt="你是 Mimir 的 RequirementDetail 分析器，只输出合法 JSON。",
        )


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

    async def analyze(self, prompt: str) -> TextGeneration:
        return await self._generate(
            model=self._model,
            prompt=prompt,
            system_prompt="你是 Mimir 的 feedback analyzer，只输出合法 JSON。",
        )


def extract_response_text(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if isinstance(response, dict):
        choices = response.get("choices")
    if not choices:
        return ""

    choice = choices[0]
    message = getattr(choice, "message", None)
    if isinstance(choice, dict):
        message = choice.get("message")
    content = getattr(message, "content", None)
    if isinstance(message, dict):
        content = message.get("content")
    return _coerce_text(content)


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
