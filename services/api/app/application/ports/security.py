from typing import Protocol

from app.domain.tokens import AccessTokenPayload, TaskTokenPayload


class TaskTokenSigner(Protocol):
    def sign(self, payload: TaskTokenPayload) -> str: ...

    def verify(self, token: str) -> TaskTokenPayload: ...


class AccessTokenSigner(Protocol):
    def sign(self, payload: AccessTokenPayload) -> str: ...

    def verify(self, token: str) -> AccessTokenPayload: ...
