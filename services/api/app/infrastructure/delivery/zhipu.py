import json
from typing import Any

from app.application.dto.invocation import LLMInvocation, PromptBundle
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
from app.application.services.llm import RetryableLLMError
from app.core.json_utils import strip_markdown_code_fence
from app.infrastructure.research.real_http import _coerce_optional_string
from app.infrastructure.llm.zhipu import (
    ZhipuChatClient,
    ZhipuClientProtocol,
)


class ZhipuOutlineAgent:
    def __init__(self, *, client: ZhipuChatClient | ZhipuClientProtocol, model: str) -> None:
        self._client = _coerce_chat_client(client)
        self._model = model

    async def prepare(self, invocation: OutlineInvocation) -> OutlineDecision:
        payload = await _complete_json(
            client=self._client,
            invocation=invocation,
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
    def __init__(self, *, client: ZhipuChatClient | ZhipuClientProtocol, model: str) -> None:
        self._client = _coerce_chat_client(client)
        self._model = model

    async def write(self, invocation: WriterInvocation) -> WriterDecision:
        payload = await _complete_json(
            client=self._client,
            invocation=invocation,
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
    invocation: OutlineInvocation | WriterInvocation,
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
    except RetryableLLMError as exc:
        raise RetryableOperationError("zhipu upstream request failed") from exc
    try:
        payload = json.loads(strip_markdown_code_fence(result.text))
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


def _coerce_chat_client(
    client: ZhipuChatClient | ZhipuClientProtocol,
) -> ZhipuChatClient:
    if isinstance(client, ZhipuChatClient):
        return client
    return ZhipuChatClient(client=client)


def _json_instruction_for_invocation(
    invocation: OutlineInvocation | WriterInvocation,
) -> str:
    if isinstance(invocation, OutlineInvocation):
        return (
            '请输出合法 JSON：{"deltas": string[], "research_outline": {"title": string, '
            '"sections": [{"section_id": string, "title": string, "description": string, '
            '"order": number}], "entities": string[]}}。'
            "不要输出 Markdown 代码块，不要输出额外解释。"
        )
    return (
        '请输出合法 JSON：{"reasoning_deltas": string[], "content_deltas": string[], '
        '"tool_calls": [{"tool_call_id": string, "tool_name": "python_interpreter", "code": string}], '
        '"final_markdown": string}。不要输出 Markdown 代码块，不要输出额外解释。'
    )
