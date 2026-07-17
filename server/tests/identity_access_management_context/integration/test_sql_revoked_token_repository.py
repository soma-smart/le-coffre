from datetime import UTC, datetime
from uuid import uuid4

from identity_access_management_context.application.gateways import Token


def test_should_store_and_find_revoked_token(sql_revoked_token_repository):
    now = datetime(2026, 7, 13, tzinfo=UTC)
    token = Token(
        value="revoked-token",
        user_id=uuid4(),
        email="user@example.com",
        roles=["user"],
        claims={},
        jti="revoked-token-jti",
        issued_at=now,
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
        token_type="access",
    )

    sql_revoked_token_repository.revoke(token, "logout", now)

    assert sql_revoked_token_repository.is_revoked("revoked-token-jti", now) is True


def test_should_purge_expired_revoked_token(sql_revoked_token_repository):
    revoked_at = datetime(2026, 7, 13, tzinfo=UTC)
    now = datetime(2026, 7, 14, tzinfo=UTC)
    token = Token(
        value="expired-token",
        user_id=uuid4(),
        email="user@example.com",
        roles=["user"],
        claims={},
        jti="expired-token-jti",
        issued_at=revoked_at,
        expires_at=revoked_at,
        token_type="refresh",
    )

    sql_revoked_token_repository.revoke(token, "refresh_token_rotated", revoked_at)

    assert sql_revoked_token_repository.is_revoked("expired-token-jti", now) is False
