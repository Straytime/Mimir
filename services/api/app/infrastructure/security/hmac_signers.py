from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime
import hashlib
import hmac
import json
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

from app.domain.tokens import AccessTokenPayload, TaskTokenPayload


PayloadT = TypeVar("PayloadT", bound=BaseModel)


class TokenVerificationError(Exception):
    """Raised when a signed token cannot be verified."""


class _HMACSigner(Generic[PayloadT]):
    def __init__(self, *, secret: str, payload_model: type[PayloadT]) -> None:
        self.secret = secret.encode("utf-8")
        self.payload_model = payload_model

    def sign(self, payload: PayloadT) -> str:
        raw_payload = json.dumps(
            payload.model_dump(mode="json"),
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        signature = hmac.new(
            self.secret,
            raw_payload,
            hashlib.sha256,
        ).digest()
        return ".".join(
            [
                self._encode(raw_payload),
                self._encode(signature),
            ]
        )

    def verify(self, token: str) -> PayloadT:
        try:
            encoded_payload, encoded_signature = token.split(".", maxsplit=1)
            raw_payload = self._decode(encoded_payload)
            provided_signature = self._decode(encoded_signature)
        except ValueError as exc:
            raise TokenVerificationError("Malformed token") from exc

        expected_signature = hmac.new(
            self.secret,
            raw_payload,
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(provided_signature, expected_signature):
            raise TokenVerificationError("Token signature mismatch")

        try:
            payload = self.payload_model.model_validate_json(raw_payload)
        except ValidationError as exc:
            raise TokenVerificationError("Token payload is invalid") from exc

        if payload.expires_at <= datetime.now(UTC):
            raise TokenVerificationError("Token expired")

        return payload

    @staticmethod
    def _encode(raw_value: bytes) -> str:
        return urlsafe_b64encode(raw_value).decode("utf-8").rstrip("=")

    @staticmethod
    def _decode(encoded_value: str) -> bytes:
        padding = "=" * (-len(encoded_value) % 4)
        return urlsafe_b64decode(encoded_value + padding)


class HMACTaskTokenSigner(_HMACSigner[TaskTokenPayload]):
    def __init__(self, *, secret: str) -> None:
        super().__init__(secret=secret, payload_model=TaskTokenPayload)


class HMACAccessTokenSigner(_HMACSigner[AccessTokenPayload]):
    def __init__(self, *, secret: str) -> None:
        super().__init__(secret=secret, payload_model=AccessTokenPayload)
