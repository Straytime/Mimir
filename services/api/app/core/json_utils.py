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
