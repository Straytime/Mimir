import re

from app.application.dto.clarification import (
    ClarificationOption,
    ClarificationQuestion,
    ClarificationQuestionSet,
)


class ClarificationOptionsParseError(Exception):
    pass


_QUESTION_PATTERNS = (
    re.compile(
        r"^\s*(?:问题\s*\d+|question\s*\d+|q\s*\d+|\d+)\s*[\.\):：、-]?\s*(?P<text>.+)$",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*(?P<text>.+[？?])\s*$"),
)
_OPTION_PATTERN = re.compile(
    r"^\s*(?:[-*]\s*)?(?:option\s*[a-z0-9]+|选项\s*[a-z0-9]+|[a-z]|\d+|[①②③④⑤⑥])[\.\):：、\-\s]+(?P<text>.+)$",
    re.IGNORECASE,
)
_BULLET_OPTION_PATTERN = re.compile(r"^\s*[-*]\s+(?P<text>.+)$")


class ClarificationOptionsParser:
    def parse(self, raw_text: str) -> ClarificationQuestionSet:
        questions: list[ClarificationQuestion] = []
        current_question: str | None = None
        current_options: list[str] = []

        def flush() -> None:
            nonlocal current_question, current_options
            if current_question and current_options:
                question_id = f"q_{len(questions) + 1}"
                options = [
                    ClarificationOption(
                        option_id=f"o_{index}",
                        label=label,
                    )
                    for index, label in enumerate(current_options, start=1)
                ]
                options.append(
                    ClarificationOption(option_id="o_auto", label="自动")
                )
                questions.append(
                    ClarificationQuestion(
                        question_id=question_id,
                        question=current_question,
                        options=options,
                    )
                )
            current_question = None
            current_options = []

        for raw_line in raw_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            question_text = self._match_question(line)
            if question_text is not None:
                flush()
                current_question = question_text
                if len(questions) == 5:
                    break
                continue

            option_text = self._match_option(line)
            if option_text is not None and current_question is not None:
                current_options.append(option_text)

        if len(questions) < 5:
            flush()

        if not questions:
            raise ClarificationOptionsParseError(
                "LLM clarification output could not be parsed into a question set."
            )

        return ClarificationQuestionSet(questions=questions[:5])

    def _match_question(self, line: str) -> str | None:
        for pattern in _QUESTION_PATTERNS:
            matched = pattern.match(line)
            if matched is None:
                continue
            text = matched.group("text").strip()
            if text:
                return text
        return None

    def _match_option(self, line: str) -> str | None:
        matched = _OPTION_PATTERN.match(line)
        if matched is None:
            bullet_matched = _BULLET_OPTION_PATTERN.match(line)
            if bullet_matched is None:
                return None
            text = bullet_matched.group("text").strip()
            return text or None
        text = matched.group("text").strip()
        return text or None
