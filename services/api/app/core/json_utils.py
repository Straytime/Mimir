import json
import re

_MARKDOWN_CODE_FENCE_RE = re.compile(
    r"^\s*```(?:json|JSON)?\s*\n(?P<body>.*)\n\s*```\s*$",
    re.DOTALL,
)


def strip_markdown_code_fence(text: str) -> str:
    stripped = text.strip()
    match = _MARKDOWN_CODE_FENCE_RE.fullmatch(stripped)
    if match is None:
        return stripped
    return match.group("body").strip()


def extract_first_top_level_json_block(text: str) -> str | None:
    sources: list[str] = []
    stripped = text.strip()
    if stripped:
        sources.append(stripped)
    unfenced = strip_markdown_code_fence(text)
    if unfenced and unfenced not in sources:
        sources.append(unfenced)

    for source in sources:
        for index, char in enumerate(source):
            if char not in "{[":
                continue
            candidate = _extract_balanced_json_candidate(source, index)
            if candidate is None:
                continue
            try:
                json.loads(candidate)
            except json.JSONDecodeError:
                continue
            return candidate
    return None


def _extract_balanced_json_candidate(text: str, start: int) -> str | None:
    stack = [text[start]]
    in_string = False
    escaped = False

    for index in range(start + 1, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char in "{[":
            stack.append(char)
            continue
        if char not in "}]":
            continue
        if not stack:
            return None

        expected = "}" if stack[-1] == "{" else "]"
        if char != expected:
            return None
        stack.pop()
        if not stack:
            return text[start : index + 1]

    return None
