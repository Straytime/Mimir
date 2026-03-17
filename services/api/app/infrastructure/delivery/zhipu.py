import json
from typing import Any

from app.application.dto.delivery import (
    OutlineDecision,
    OutlineInvocation,
    OutlineSection,
    ResearchOutline,
    WriterDecision,
    WriterInvocation,
    WriterToolCall,
)
from app.application.services.invocation import RetryableOperationError
from app.infrastructure.research.real_http import _coerce_optional_string, _strip_code_fences
from app.infrastructure.llm.zhipu import ZhipuChatClient, map_zhipu_exception


class ZhipuOutlineAgent:
    def __init__(self, *, client: ZhipuChatClient, model: str) -> None:
        self._client = client
        self._model = model

    async def prepare(self, invocation: OutlineInvocation) -> OutlineDecision:
        payload = await _complete_json(
            client=self._client,
            model=self._model,
            prompt=(
                f"{invocation.prompt_name}\n"
                '请输出合法 JSON：{"deltas": string[], "research_outline": {"title": string, "sections": [{"section_id": string, "title": string, "description": string, "order": number}], "entities": string[]}}。'
            ),
        )
        outline_payload = payload.get("research_outline")
        if not isinstance(outline_payload, dict):
            raise RetryableOperationError("zhipu returned invalid outline JSON")
        raw_sections = outline_payload.get("sections")
        if not isinstance(raw_sections, list):
            raise RetryableOperationError("zhipu returned invalid outline JSON")
        sections = []
        for index, item in enumerate(raw_sections, start=1):
            if not isinstance(item, dict):
                continue
            title = _coerce_optional_string(item.get("title"))
            description = _coerce_optional_string(item.get("description"))
            if not title or not description:
                continue
            sections.append(
                OutlineSection(
                    section_id=str(item.get("section_id") or f"sec_{index}"),
                    title=title,
                    description=description,
                    order=int(item.get("order", index)),
                )
            )
        if not sections:
            raise RetryableOperationError("zhipu returned invalid outline JSON")
        entities = outline_payload.get("entities")
        if isinstance(entities, (list, tuple)):
            entity_values = tuple(
                str(item).strip() for item in entities if str(item).strip()
            )
        else:
            entity_values = ()
        return OutlineDecision(
            deltas=_coerce_string_tuple(payload.get("deltas")),
            outline=ResearchOutline(
                title=str(outline_payload.get("title") or "研究报告").strip(),
                sections=tuple(sections),
                entities=entity_values,
            ),
        )


class ZhipuWriterAgent:
    def __init__(self, *, client: ZhipuChatClient, model: str) -> None:
        self._client = client
        self._model = model

    async def write(self, invocation: WriterInvocation) -> WriterDecision:
        payload = await _complete_json(
            client=self._client,
            model=self._model,
            prompt=(
                f"{invocation.prompt_name}\n"
                '请输出合法 JSON：{"reasoning_deltas": string[], "content_deltas": string[], "tool_calls": [{"tool_call_id": string, "tool_name": "python_interpreter", "code": string}], "final_markdown": string}。'
            ),
        )
        raw_tool_calls = payload.get("tool_calls") or ()
        tool_calls: list[WriterToolCall] = []
        for index, item in enumerate(raw_tool_calls, start=1):
            if not isinstance(item, dict):
                continue
            tool_name = str(item.get("tool_name") or "").strip()
            code = _coerce_optional_string(item.get("code"))
            if tool_name != "python_interpreter" or not code:
                continue
            tool_calls.append(
                WriterToolCall(
                    tool_call_id=str(
                        item.get("tool_call_id") or f"writer_tool_{index}"
                    ),
                    tool_name=tool_name,
                    code=code,
                )
            )
        final_markdown = _coerce_optional_string(payload.get("final_markdown"))
        if final_markdown is None:
            raise RetryableOperationError("zhipu returned invalid writer JSON")
        return WriterDecision(
            reasoning_deltas=_coerce_string_tuple(payload.get("reasoning_deltas")),
            content_deltas=_coerce_string_tuple(payload.get("content_deltas")),
            tool_calls=tuple(tool_calls),
            final_markdown=final_markdown,
        )


async def _complete_json(
    *,
    client: ZhipuChatClient,
    model: str,
    prompt: str,
) -> dict[str, Any]:
    try:
        result = await client.complete(
            model=model,
            prompt=prompt,
            system_prompt="你是 Mimir 的结构化输出代理，只输出合法 JSON。",
        )
    except Exception as exc:  # pragma: no cover - mapped by lower-level tests
        mapped = map_zhipu_exception(exc, retryable_cls=RetryableOperationError)
        raise mapped from exc
    try:
        payload = json.loads(_strip_code_fences(result.text))
    except json.JSONDecodeError as exc:
        raise RetryableOperationError("zhipu returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RetryableOperationError("zhipu returned invalid JSON")
    return payload


def _coerce_string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        cleaned = value.strip()
        return (cleaned,) if cleaned else ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()
