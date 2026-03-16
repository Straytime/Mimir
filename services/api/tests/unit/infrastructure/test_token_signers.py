from datetime import UTC, datetime, timedelta

import pytest

from app.domain.enums import AccessTokenResourceType
from app.domain.tokens import AccessTokenPayload, TaskTokenPayload
from app.infrastructure.security.hmac_signers import (
    HMACAccessTokenSigner,
    HMACTaskTokenSigner,
    TokenVerificationError,
)


def test_task_token_signer_round_trips_payload() -> None:
    signer = HMACTaskTokenSigner(
        secret="task-secret",
        clock=lambda: datetime(2026, 3, 15, 13, 0, tzinfo=UTC),
    )
    payload = TaskTokenPayload(
        task_id="tsk_01JABC",
        issued_at=datetime(2026, 3, 15, 12, 0, tzinfo=UTC),
        expires_at=datetime(2026, 3, 16, 12, 0, tzinfo=UTC),
    )

    token = signer.sign(payload)

    assert signer.verify(token) == payload


def test_access_token_signer_rejects_tampered_tokens() -> None:
    signer = HMACAccessTokenSigner(secret="access-secret")
    payload = AccessTokenPayload(
        task_id="tsk_01JABC",
        resource_type=AccessTokenResourceType.ARTIFACT,
        resource_scope="art_01JABC",
        issued_at=datetime(2026, 3, 15, 12, 0, tzinfo=UTC),
        expires_at=datetime(2026, 3, 15, 12, 10, tzinfo=UTC),
    )

    token = signer.sign(payload)

    with pytest.raises(TokenVerificationError):
        signer.verify(f"{token}tampered")
