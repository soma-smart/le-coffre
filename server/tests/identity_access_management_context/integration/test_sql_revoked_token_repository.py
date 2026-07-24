from datetime import UTC, datetime
from uuid import uuid4

from sqlmodel import select

from identity_access_management_context.adapters.secondary.sql.model.revoked_token_model import (
    RevokedTokenTable,
)
from identity_access_management_context.application.gateways import (
    REVOCATION_REASON_LOGOUT,
    REVOCATION_REASON_REFRESH_TOKEN_ROTATED,
    ActiveRevocation,
    Token,
)


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


def test_should_expose_active_revocation_reason(sql_revoked_token_repository):
    revoked_at = datetime(2026, 7, 13, tzinfo=UTC)
    now = datetime(2026, 7, 14, tzinfo=UTC)
    rotated_token = Token(
        value="rotated-token",
        user_id=uuid4(),
        email="user@example.com",
        roles=["user"],
        claims={},
        jti="rotated-token-jti",
        issued_at=revoked_at,
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
        token_type="refresh",
    )
    expired_token = Token(
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

    sql_revoked_token_repository.revoke(rotated_token, REVOCATION_REASON_REFRESH_TOKEN_ROTATED, revoked_at)
    sql_revoked_token_repository.revoke(expired_token, REVOCATION_REASON_LOGOUT, revoked_at)

    assert sql_revoked_token_repository.get_active_revocation("rotated-token-jti", now) == ActiveRevocation(
        reason=REVOCATION_REASON_REFRESH_TOKEN_ROTATED
    )
    assert sql_revoked_token_repository.get_active_revocation("expired-token-jti", now) is None
    assert sql_revoked_token_repository.get_active_revocation("unknown-jti", now) is None


def test_should_keep_first_revocation_when_same_jti_revoked_twice(sql_revoked_token_repository, session):
    now = datetime(2026, 7, 13, tzinfo=UTC)
    later = datetime(2026, 7, 13, 1, tzinfo=UTC)
    token = Token(
        value="raced-token",
        user_id=uuid4(),
        email="user@example.com",
        roles=["user"],
        claims={},
        jti="raced-token-jti",
        issued_at=now,
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
        token_type="refresh",
    )

    sql_revoked_token_repository.revoke(token, REVOCATION_REASON_REFRESH_TOKEN_ROTATED, now)
    # A concurrent revocation of the same jti must be a silent no-op, not a 500.
    sql_revoked_token_repository.revoke(token, REVOCATION_REASON_LOGOUT, later)

    all_rows = session.exec(select(RevokedTokenTable).where(RevokedTokenTable.jti == "raced-token-jti")).all()
    assert len(all_rows) == 1
    assert all_rows[0].reason == REVOCATION_REASON_REFRESH_TOKEN_ROTATED


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


def test_should_not_purge_expired_tokens_implicitly_on_revoke(sql_revoked_token_repository, session):
    revoked_at = datetime(2026, 7, 13, tzinfo=UTC)
    now = datetime(2026, 7, 14, tzinfo=UTC)

    expired_token = Token(
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
    active_token = Token(
        value="active-token",
        user_id=uuid4(),
        email="user@example.com",
        roles=["user"],
        claims={},
        jti="active-token-jti",
        issued_at=revoked_at,
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
        token_type="access",
    )

    sql_revoked_token_repository.revoke(expired_token, "refresh_token_rotated", revoked_at)
    sql_revoked_token_repository.revoke(active_token, "logout", now)

    all_rows = session.exec(select(RevokedTokenTable)).all()
    assert len(all_rows) == 2


def test_should_purge_expired_tokens_when_called_explicitly(sql_revoked_token_repository, session):
    revoked_at = datetime(2026, 7, 13, tzinfo=UTC)
    now = datetime(2026, 7, 14, tzinfo=UTC)

    expired_token = Token(
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
    active_token = Token(
        value="active-token",
        user_id=uuid4(),
        email="user@example.com",
        roles=["user"],
        claims={},
        jti="active-token-jti",
        issued_at=revoked_at,
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
        token_type="access",
    )

    sql_revoked_token_repository.revoke(expired_token, "refresh_token_rotated", revoked_at)
    sql_revoked_token_repository.revoke(active_token, "logout", revoked_at)

    sql_revoked_token_repository.purge_expired(now)

    all_rows = session.exec(select(RevokedTokenTable)).all()
    remaining_jtis = {row.jti for row in all_rows}
    assert remaining_jtis == {"active-token-jti"}
