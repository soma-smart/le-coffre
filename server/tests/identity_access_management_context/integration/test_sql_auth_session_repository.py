from datetime import UTC, datetime
from uuid import uuid4


def test_should_create_and_lookup_active_session(sql_auth_session_repository):
    user_id = uuid4()
    now = datetime(2026, 7, 23, tzinfo=UTC)

    sql_auth_session_repository.create_session(user_id, "refresh-jti-1", now)

    session = sql_auth_session_repository.get_active_by_user_id_and_refresh_jti(user_id, "refresh-jti-1")
    assert session is not None
    assert session.user_id == user_id
    assert session.current_refresh_token_jti == "refresh-jti-1"


def test_should_rotate_session_refresh_jti(sql_auth_session_repository):
    user_id = uuid4()
    now = datetime(2026, 7, 23, tzinfo=UTC)

    session = sql_auth_session_repository.create_session(user_id, "refresh-jti-1", now)
    rotated = sql_auth_session_repository.rotate_refresh_token_jti(session.id, "refresh-jti-1", "refresh-jti-2", now)

    assert rotated is True
    old_lookup = sql_auth_session_repository.get_active_by_user_id_and_refresh_jti(user_id, "refresh-jti-1")
    new_lookup = sql_auth_session_repository.get_active_by_user_id_and_refresh_jti(user_id, "refresh-jti-2")
    assert old_lookup is None
    assert new_lookup is not None


def test_should_not_rotate_when_expected_jti_does_not_match(sql_auth_session_repository):
    user_id = uuid4()
    now = datetime(2026, 7, 23, tzinfo=UTC)

    session = sql_auth_session_repository.create_session(user_id, "refresh-jti-1", now)
    rotated = sql_auth_session_repository.rotate_refresh_token_jti(
        session.id, "already-rotated-jti", "refresh-jti-2", now
    )

    assert rotated is False
    unchanged = sql_auth_session_repository.get_active_by_user_id_and_refresh_jti(user_id, "refresh-jti-1")
    assert unchanged is not None


def test_should_not_rotate_invalidated_session(sql_auth_session_repository):
    user_id = uuid4()
    now = datetime(2026, 7, 23, tzinfo=UTC)

    session = sql_auth_session_repository.create_session(user_id, "refresh-jti-1", now)
    sql_auth_session_repository.invalidate_all_for_user(user_id, now)
    rotated = sql_auth_session_repository.rotate_refresh_token_jti(session.id, "refresh-jti-1", "refresh-jti-2", now)

    assert rotated is False


def test_should_invalidate_all_user_sessions(sql_auth_session_repository):
    user_id = uuid4()
    other_user_id = uuid4()
    now = datetime(2026, 7, 23, tzinfo=UTC)

    sql_auth_session_repository.create_session(user_id, "refresh-jti-1", now)
    sql_auth_session_repository.create_session(user_id, "refresh-jti-2", now)
    sql_auth_session_repository.create_session(other_user_id, "refresh-jti-other", now)

    sql_auth_session_repository.invalidate_all_for_user(user_id, now)

    assert sql_auth_session_repository.get_active_by_user_id_and_refresh_jti(user_id, "refresh-jti-1") is None
    assert sql_auth_session_repository.get_active_by_user_id_and_refresh_jti(user_id, "refresh-jti-2") is None
    assert (
        sql_auth_session_repository.get_active_by_user_id_and_refresh_jti(other_user_id, "refresh-jti-other")
        is not None
    )


def test_should_purge_dead_sessions(sql_auth_session_repository, session):
    from sqlmodel import select

    from identity_access_management_context.adapters.secondary.sql.model.auth_session_model import AuthSessionTable

    user_id = uuid4()
    cutoff = datetime(2026, 7, 23, tzinfo=UTC)
    before_cutoff = datetime(2026, 7, 22, tzinfo=UTC)
    after_cutoff = datetime(2026, 7, 23, 12, tzinfo=UTC)

    # Invalidated long ago -> purged
    sql_auth_session_repository.create_session(user_id, "old-invalidated-jti", before_cutoff)
    sql_auth_session_repository.invalidate_by_user_id_and_refresh_jti(user_id, "old-invalidated-jti", before_cutoff)
    # Recently invalidated -> kept
    sql_auth_session_repository.create_session(user_id, "fresh-invalidated-jti", before_cutoff)
    sql_auth_session_repository.invalidate_by_user_id_and_refresh_jti(user_id, "fresh-invalidated-jti", after_cutoff)
    # Active but idle past the refresh TTL -> purged
    sql_auth_session_repository.create_session(user_id, "stale-active-jti", before_cutoff)
    # Active and recently used -> kept
    sql_auth_session_repository.create_session(user_id, "fresh-active-jti", after_cutoff)

    sql_auth_session_repository.purge_dead(cutoff)

    remaining_jtis = {row.current_refresh_token_jti for row in session.exec(select(AuthSessionTable)).all()}
    assert remaining_jtis == {"fresh-invalidated-jti", "fresh-active-jti"}
