from typing import Protocol

from app.application.dto.invocation import LLMInvocation
from app.application.services.llm import TextGeneration


class ClarificationGenerator(Protocol):
    async def generate_natural(self, invocation: LLMInvocation) -> TextGeneration: ...

    async def generate_options(self, invocation: LLMInvocation) -> TextGeneration: ...


class RequirementAnalyzer(Protocol):
    async def analyze(self, invocation: LLMInvocation) -> TextGeneration: ...


class FeedbackAnalyzer(Protocol):
    async def analyze(self, invocation: LLMInvocation) -> TextGeneration: ...
