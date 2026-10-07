"""One behaviour for both share link repositories.

The use case tests run on FakeShareLinkRepository, production on
SqlShareLinkRepository, and each restates the link lifecycle in its own terms
(entity methods for one, WHERE clauses for the other). Running the same
scenarios against both keeps a rule changed on one side only from passing
unnoticed.
"""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from tests.vault_management_context.unit.fakes import FakeShareLinkRepository
from vault_management_context.adapters.secondary import SqlShareLinkRepository
from vault_management_context.domain.entities import SHARE_LINK_LIFETIME, SHARE_LINK_REOPEN_WINDOW, ShareLink

NOW = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
EXPIRY = NOW + SHARE_LINK_LIFETIME


@pytest.fixture(params=["fake", "sql"])
def repository(request, session):
    if request.param == "fake":
        return FakeShareLinkRepository()
    return SqlShareLinkRepository(session)


def _lookup(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()


def _links(setup_id: str, count: int, now: datetime = NOW) -> list[ShareLink]:
    return [
        ShareLink.create(
            setup_id=setup_id,
            share_index=index,
            lookup_hash=_lookup(f"{setup_id}-{index}"),
            ack_hash=_lookup(f"ack-{setup_id}-{index}"),
            sealed_share=f"sealed-{setup_id}-{index}",
            now=now,
        )
        for index in range(1, count + 1)
    ]


def _deliver(repository, link: ShareLink, at: datetime):
    # As the use case does: the window is the entity's to compute
    return repository.deliver(link.id, at, link.reopen_deadline(at))


def _indexes(repository, links: list[ShareLink]) -> list[int]:
    return [link.share_index for link in links if repository.get_by_lookup_hash(link.lookup_hash) is not None]


def test_replace_all_then_get_by_lookup_hash_round_trips_the_link(repository):
    links = _links("s1", 3)
    repository.replace_all(links)

    assert repository.get_by_lookup_hash(_lookup("s1-2")) == links[1]
    assert repository.get_by_lookup_hash(_lookup("nope")) is None


def test_replace_all_drops_the_links_of_a_previous_setup(repository):
    old, new = _links("old", 3), _links("new", 2)
    repository.replace_all(old)
    repository.replace_all(new)

    assert _indexes(repository, old) == []
    assert _indexes(repository, new) == [1, 2]


def test_first_delivery_starts_the_reopen_window_and_keeps_the_link(repository):
    link = _links("s1", 1)[0]
    repository.replace_all([link])
    at = NOW + timedelta(hours=3)

    delivery = _deliver(repository, link, at)

    assert delivery is not None
    assert (delivery.first_delivered_at, delivery.reopened) == (at, False)
    assert delivery.reopenable_until == at + SHARE_LINK_REOPEN_WINDOW
    stored = repository.get_by_lookup_hash(link.lookup_hash)
    assert stored is not None and stored.delivered_at == at


def test_delivery_within_the_window_is_a_reopening_that_keeps_the_first_time(repository):
    link = _links("s1", 1)[0]
    repository.replace_all([link])
    first = NOW + timedelta(hours=3)
    _deliver(repository, link, first)

    again = _deliver(repository, link, first + SHARE_LINK_REOPEN_WINDOW - timedelta(seconds=1))

    assert again is not None
    assert (again.first_delivered_at, again.reopened) == (first, True)
    # Reopening does not push the window further
    assert again.reopenable_until == first + SHARE_LINK_REOPEN_WINDOW


def test_delivery_past_the_reopen_window_is_refused(repository):
    link = _links("s1", 1)[0]
    repository.replace_all([link])
    first = NOW + timedelta(hours=3)
    _deliver(repository, link, first)

    assert _deliver(repository, link, first + SHARE_LINK_REOPEN_WINDOW) is None


def test_delivery_refuses_an_expired_link(repository):
    link = _links("s1", 1)[0]
    repository.replace_all([link])

    assert _deliver(repository, link, EXPIRY) is None


def test_window_opened_just_before_expiry_ends_with_the_link(repository):
    link = _links("s1", 1)[0]
    repository.replace_all([link])
    first = EXPIRY - timedelta(minutes=5)

    delivery = _deliver(repository, link, first)

    # The deadline shown to the custodian is the one actually enforced
    assert delivery is not None and delivery.reopenable_until == EXPIRY
    assert _deliver(repository, link, EXPIRY - timedelta(seconds=1)) is not None
    assert _deliver(repository, link, EXPIRY) is None


def test_remove_delivered_deletes_only_a_delivered_link_and_only_once(repository):
    links = _links("s1", 2)
    repository.replace_all(links)
    assert repository.remove_delivered(links[0].id, NOW) is False

    _deliver(repository, links[0], NOW)
    assert repository.remove_delivered(links[0].id, NOW + timedelta(minutes=1)) is True
    assert repository.remove_delivered(links[0].id, NOW + timedelta(minutes=1)) is False

    assert _indexes(repository, links) == [2]


def test_remove_delivered_refuses_a_link_past_its_reopen_window(repository):
    link = _links("s1", 1)[0]
    repository.replace_all([link])
    _deliver(repository, link, NOW)

    # Closed on its own: still there until the purge, but not to be acknowledged
    assert repository.remove_delivered(link.id, NOW + SHARE_LINK_REOPEN_WINDOW) is False
    assert repository.get_by_lookup_hash(link.lookup_hash) is not None


def test_remove_delivered_refuses_an_expired_link(repository):
    link = _links("s1", 1)[0]
    repository.replace_all([link])
    _deliver(repository, link, EXPIRY - timedelta(minutes=5))

    assert repository.remove_delivered(link.id, EXPIRY) is False


def test_purge_deletes_expired_links_and_links_past_their_window_only(repository):
    links = _links("s1", 3)
    stale = _links("stale", 1, now=NOW - timedelta(hours=49))
    repository.replace_all(links + stale)
    _deliver(repository, links[0], NOW)
    _deliver(repository, links[1], NOW + timedelta(minutes=10))

    repository.purge_expired(NOW + SHARE_LINK_REOPEN_WINDOW)

    # Window over for 1; still open for 2; never opened for 3; stale expired
    assert _indexes(repository, links) == [2, 3]
    assert _indexes(repository, stale) == []
