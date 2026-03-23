from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class InvocationProfile:
    stage: str
    model: str
    temperature: float
    top_p: float
    max_tokens: int
    thinking: bool
    clear_thinking: bool | None
    stream: bool

    def provider_thinking(self) -> dict[str, Any]:
        if not self.thinking:
            return {"type": "disabled"}
        payload: dict[str, Any] = {"type": "enabled"}
        if self.clear_thinking is not None:
            payload["clear_thinking"] = self.clear_thinking
        return payload


@dataclass(frozen=True, slots=True)
class PromptMessage:
    role: str
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: tuple[dict[str, Any], ...] | None = None
    reasoning_content: str | None = None

    def to_provider_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name is not None:
            payload["name"] = self.name
        if self.tool_call_id is not None:
            payload["tool_call_id"] = self.tool_call_id
        if self.tool_calls is not None:
            payload["tool_calls"] = list(self.tool_calls)
        if self.reasoning_content is not None:
            payload["reasoning_content"] = self.reasoning_content
        return payload


@dataclass(frozen=True, slots=True)
class PromptBundle:
    system_prompt: str | None
    user_prompt: str
    transcript: tuple[PromptMessage, ...] = ()

    @property
    def messages(self) -> tuple[PromptMessage, ...]:
        messages: list[PromptMessage] = []
        if self.system_prompt is not None:
            messages.append(PromptMessage(role="system", content=self.system_prompt))
        messages.append(PromptMessage(role="user", content=self.user_prompt))
        messages.extend(self.transcript)
        return tuple(messages)


@dataclass(frozen=True, slots=True)
class ToolSchema:
    name: str
    description: str
    parameters: dict[str, Any]
    required: tuple[str, ...] = ()

    def to_provider_payload(self) -> dict[str, Any]:
        function_payload: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
            },
        }
        if self.required:
            function_payload["parameters"]["required"] = list(self.required)
        return {
            "type": "function",
            "function": function_payload,
        }


@dataclass(frozen=True, slots=True)
class LLMInvocation:
    profile: InvocationProfile
    prompt_bundle: PromptBundle
    tool_schemas: tuple[ToolSchema, ...] = ()


def dump_prompt_bundle(bundle: PromptBundle) -> dict[str, Any]:
    return {
        "system_prompt": bundle.system_prompt,
        "user_prompt": bundle.user_prompt,
        "transcript": [
            {
                "role": message.role,
                "content": message.content,
                "name": message.name,
                "tool_call_id": message.tool_call_id,
                "tool_calls": list(message.tool_calls) if message.tool_calls else None,
                "reasoning_content": message.reasoning_content,
            }
            for message in bundle.transcript
        ],
    }
