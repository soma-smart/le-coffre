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
    sql_auth_session_repository.rotate_refresh_token_jti(session.id, "refresh-jti-2", now)

    old_lookup = sql_auth_session_repository.get_active_by_user_id_and_refresh_jti(user_id, "refresh-jti-1")
    new_lookup = sql_auth_session_repository.get_active_by_user_id_and_refresh_jti(user_id, "refresh-jti-2")
    assert old_lookup is None
    assert new_lookup is not None


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
