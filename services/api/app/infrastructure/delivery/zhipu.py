import json
import logging

from app.application.dto.invocation import LLMInvocation

logger = logging.getLogger(__name__)
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
from app.application.services.invocation import OperationTraceSnapshot, TraceableOperationError
from app.application.services.llm import RetryableLLMError
from app.core.json_utils import extract_first_top_level_json_block
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
        except RetryableLLMError as exc:
            raise RetryableOperationError("zhipu upstream request failed") from exc
        extracted = extract_first_top_level_json_block(result.text)
        if extracted is None:
            logger.error("outline: invalid JSON response")
            raise TraceableOperationError(
                "zhipu returned invalid JSON",
                trace_snapshot=_build_trace_snapshot(result),
            )
        try:
            payload = json.loads(extracted)
        except json.JSONDecodeError as exc:
            logger.error("outline: invalid JSON response", exc_info=True)
            raise TraceableOperationError(
                "zhipu returned invalid JSON",
                trace_snapshot=_build_trace_snapshot(result),
            ) from exc
        if not isinstance(payload, dict):
            raise TraceableOperationError(
                "zhipu returned invalid outline JSON",
                trace_snapshot=_build_trace_snapshot(result),
            )

        outline_payload = payload.get("research_outline")
        if not isinstance(outline_payload, dict):
            raise TraceableOperationError(
                "zhipu returned invalid outline JSON",
                trace_snapshot=_build_trace_snapshot(result),
            )

        title = "研究报告"
        sections: list[OutlineSection] = []
        order = 0
        for key, value in outline_payload.items():
            if not isinstance(value, dict):
                continue
            if key == "标题":
                title = str(value.get("title") or "研究报告").strip()
                continue
            item_title = _coerce_optional_string(value.get("title"))
            item_desc = _coerce_optional_string(value.get("description"))
            if not item_title or not item_desc:
                continue
            order += 1
            sections.append(
                OutlineSection(
                    section_id=key,
                    title=item_title,
                    description=item_desc,
                    order=order,
                )
            )
        if not sections:
            raise TraceableOperationError(
                "zhipu returned invalid outline JSON",
                trace_snapshot=_build_trace_snapshot(result),
            )

        entities = payload.get("entities")
        if isinstance(entities, (list, tuple)):
            entity_values = tuple(
                str(item).strip() for item in entities if str(item).strip()
            )
        else:
            entity_values = ()
        return OutlineDecision(
            deltas=(),
            outline=ResearchOutline(
                title=title,
                sections=tuple(sections),
                entities=entity_values,
            ),
            request_id=result.request_id,
            provider_finish_reason=result.provider_finish_reason,
            provider_usage=result.provider_usage,
            request_payload=result.request_payload,
            response_payload=result.response_payload,
        )


class ZhipuWriterAgent:
    def __init__(self, *, client: ZhipuChatClient | ZhipuClientProtocol, model: str) -> None:
        self._client = _coerce_chat_client(client)
        self._model = model

    async def write(self, invocation: WriterInvocation) -> WriterDecision:
        if invocation.prompt_bundle is None or invocation.profile is None:
            raise RetryableOperationError("zhipu invocation contract is incomplete")
        logger.info("writer round starting: prompt_name=%s", invocation.prompt_name)
        try:
            result = await self._client.complete(
                invocation=LLMInvocation(
                    profile=invocation.profile,
                    prompt_bundle=invocation.prompt_bundle,
                    tool_schemas=invocation.tool_schemas,
                )
            )
        except RetryableLLMError as exc:
            raise RetryableOperationError("zhipu upstream request failed") from exc

        tool_calls: list[WriterToolCall] = []
        for index, tc in enumerate(result.tool_calls, start=1):
            name = tc.get("name", "")
            if name != "python_interpreter":
                continue
            try:
                args = json.loads(tc.get("arguments", "{}"))
            except json.JSONDecodeError:
                continue
            code = args.get("code", "").strip()
            if not code:
                continue
            tool_calls.append(
                WriterToolCall(
                    tool_call_id=tc.get("id") or f"writer_tool_{index}",
                    tool_name="python_interpreter",
                    code=code,
                )
            )
        return WriterDecision(
            text=result.text.strip(),
            tool_calls=tuple(tool_calls),
            reasoning_text=result.reasoning_text.strip(),
            request_id=result.request_id,
            provider_finish_reason=result.provider_finish_reason,
            provider_usage=result.provider_usage,
            request_payload=result.request_payload,
            response_payload=result.response_payload,
        )


def _coerce_chat_client(
    client: ZhipuChatClient | ZhipuClientProtocol,
) -> ZhipuChatClient:
    if isinstance(client, ZhipuChatClient):
        return client
    return ZhipuChatClient(client=client)


def _build_trace_snapshot(result) -> OperationTraceSnapshot:
    return OperationTraceSnapshot(
        parsed_text=result.text,
        reasoning_text=result.reasoning_text.strip(),
        tool_calls_json=tuple(dict(tool_call) for tool_call in (result.tool_calls or ())),
        provider_finish_reason=result.provider_finish_reason,
        provider_usage_json=result.provider_usage,
        request_id=result.request_id,
        request_payload=result.request_payload,
        response_payload=result.response_payload,
    )
