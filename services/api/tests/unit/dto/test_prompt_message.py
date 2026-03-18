from app.application.dto.invocation import PromptMessage


def test_prompt_message_tool_calls_in_payload() -> None:
    """PromptMessage with tool_calls should include them in payload."""
    tool_calls = (
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "collect_agent", "arguments": "{}"},
        },
    )
    msg = PromptMessage(role="assistant", content="", tool_calls=tool_calls)
    payload = msg.to_provider_payload()

    assert payload["role"] == "assistant"
    assert payload["content"] == ""
    assert "tool_calls" in payload
    assert payload["tool_calls"] == list(tool_calls)


def test_prompt_message_no_tool_calls_omits_field() -> None:
    """PromptMessage without tool_calls should not include tool_calls in payload."""
    msg = PromptMessage(role="user", content="hello")
    payload = msg.to_provider_payload()

    assert "tool_calls" not in payload
    assert payload == {"role": "user", "content": "hello"}
