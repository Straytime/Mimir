from typing import Protocol

from app.application.services.llm import TextGeneration


class ClarificationGenerator(Protocol):
    async def generate_natural(self, prompt: str) -> TextGeneration: ...

    async def generate_options(self, prompt: str) -> TextGeneration: ...


class RequirementAnalyzer(Protocol):
    async def analyze(self, prompt: str) -> TextGeneration: ...


class FeedbackAnalyzer(Protocol):
    async def analyze(self, prompt: str) -> TextGeneration: ...
