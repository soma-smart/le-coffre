import logging

from vault_management_context.adapters.secondary.in_memory_share_repository import (
    MAX_PENDING_SESSIONS,
    MAX_PENDING_SHARES_PER_SESSION,
    InMemoryShareRepository,
)
from vault_management_context.domain.entities import Share
from vault_management_context.domain.value_objects import UnlockSessionId

SESSION = UnlockSessionId("SESSIONAAAAAAAAA")
OTHER_SESSION = UnlockSessionId("SESSIONBBBBBBBBB")


def _session(i: int) -> UnlockSessionId:
    return UnlockSessionId(f"SESSION{i:09d}")


def test_should_cap_pending_shares_to_bound_memory():
    repo = InMemoryShareRepository()

    repo.add(SESSION, [Share(f"{i}:x") for i in range(MAX_PENDING_SHARES_PER_SESSION + 25)])

    assert len(repo.get_all(SESSION)) == MAX_PENDING_SHARES_PER_SESSION


def test_should_warn_when_dropping_shares_at_capacity(caplog):
    repo = InMemoryShareRepository()
    repo.add(SESSION, [Share(f"{i}:x") for i in range(MAX_PENDING_SHARES_PER_SESSION)])

    with caplog.at_level(logging.WARNING):
        repo.add(SESSION, [Share("extra:1"), Share("extra:2")])

    assert "at capacity" in caplog.text
    assert len(repo.get_all(SESSION)) == MAX_PENDING_SHARES_PER_SESSION


def test_should_append_without_deduplicating():
    # The store is a dumb sink: deduplication is the use case's responsibility.
    repo = InMemoryShareRepository()

    repo.add(SESSION, [Share("0:a"), Share("0:a")])

    assert len(repo.get_all(SESSION)) == 2


def test_should_keep_shares_of_each_session_apart():
    repo = InMemoryShareRepository()

    repo.add(SESSION, [Share("0:a")])
    repo.add(OTHER_SESSION, [Share("1:b"), Share("2:c")])

    assert [s.secret for s in repo.get_all(SESSION)] == ["0:a"]
    assert [s.secret for s in repo.get_all(OTHER_SESSION)] == ["1:b", "2:c"]
    assert repo.get_last_share_timestamp(SESSION) is not None


def test_given_unknown_session_should_have_no_share_nor_timestamp():
    repo = InMemoryShareRepository()

    assert repo.get_all(SESSION) == []
    assert repo.get_last_share_timestamp(SESSION) is None


def test_given_empty_submission_should_not_open_a_session():
    repo = InMemoryShareRepository()

    repo.add(SESSION, [])

    assert repo.get_last_share_timestamp(SESSION) is None


def test_clear_should_drop_every_session():
    repo = InMemoryShareRepository()
    repo.add(SESSION, [Share("0:a")])
    repo.add(OTHER_SESSION, [Share("1:b")])

    repo.clear()

    assert repo.get_all(SESSION) == []
    assert repo.get_all(OTHER_SESSION) == []
    assert repo.get_last_share_timestamp(SESSION) is None


def test_given_too_many_sessions_should_evict_the_least_recently_active(caplog):
    repo = InMemoryShareRepository()
    for i in range(MAX_PENDING_SESSIONS):
        repo.add(_session(i), [Share(f"{i}:x")])
    # Session 0 is the oldest one but becomes the most recently active.
    repo.add(_session(0), [Share("0:y")])

    with caplog.at_level(logging.WARNING):
        repo.add(_session(MAX_PENDING_SESSIONS), [Share("new:x")])

    assert "evicted" in caplog.text
    assert repo.get_all(_session(1)) == []
    assert len(repo.get_all(_session(0))) == 2
    assert len(repo.get_all(_session(MAX_PENDING_SESSIONS))) == 1
