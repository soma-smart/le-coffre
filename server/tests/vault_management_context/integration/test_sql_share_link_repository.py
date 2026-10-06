import hashlib
from datetime import UTC, datetime, timedelta, timezone

from sqlmodel import Session, select

from vault_management_context.adapters.secondary import SqlShareLinkRepository
from vault_management_context.adapters.secondary.sql import VaultShareLinkTable
from vault_management_context.domain.entities import ShareLink

NOW = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


def _lookup(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()


def _links(setup_id: str, count: int, now: datetime = NOW) -> list[ShareLink]:
    return [
        ShareLink.create(
            setup_id=setup_id,
            share_index=index,
            lookup_hash=_lookup(f"{setup_id}-{index}"),
            sealed_share=f"sealed-{setup_id}-{index}",
            now=now,
        )
        for index in range(1, count + 1)
    ]


def _stored_rows(session: Session) -> list[VaultShareLinkTable]:
    session.expire_all()
    return list(session.exec(select(VaultShareLinkTable)).all())


def test_replace_all_then_get_by_lookup_hash_round_trips_the_link(share_link_repository: SqlShareLinkRepository):
    links = _links("s1", 3)
    share_link_repository.replace_all(links)

    stored = share_link_repository.get_by_lookup_hash(_lookup("s1-2"))

    assert stored == links[1]
    # Datetimes come back aware, so they compare with what TimeGateway hands out.
    assert stored is not None and stored.expires_at.tzinfo is not None


def test_get_by_lookup_hash_returns_none_for_unknown_hash(share_link_repository: SqlShareLinkRepository):
    share_link_repository.replace_all(_links("s1", 2))
    assert share_link_repository.get_by_lookup_hash(_lookup("nope")) is None


def test_replace_all_drops_the_links_of_a_previous_setup(
    share_link_repository: SqlShareLinkRepository, session: Session
):
    share_link_repository.replace_all(_links("old", 5))
    share_link_repository.replace_all(_links("new", 2))

    assert sorted((row.setup_id, row.share_index) for row in _stored_rows(session)) == [("new", 1), ("new", 2)]


def test_consume_deletes_the_link_and_only_succeeds_once(
    share_link_repository: SqlShareLinkRepository, session: Session
):
    links = _links("s1", 2)
    share_link_repository.replace_all(links)
    at = NOW + timedelta(hours=3)

    assert share_link_repository.consume(links[0].id, at) is True
    assert share_link_repository.consume(links[0].id, at) is False

    assert [row.lookup_hash for row in _stored_rows(session)] == [links[1].lookup_hash]


def test_consume_refuses_an_expired_link(share_link_repository: SqlShareLinkRepository):
    links = _links("s1", 1)
    share_link_repository.replace_all(links)

    assert share_link_repository.consume(links[0].id, NOW + timedelta(hours=48)) is False


def test_consume_compares_expiry_in_utc_whatever_the_caller_offset(share_link_repository: SqlShareLinkRepository):
    links = _links("s1", 1)
    share_link_repository.replace_all(links)
    # One minute before expiry, expressed at UTC+2: still valid.
    just_before = (links[0].expires_at - timedelta(minutes=1)).astimezone(timezone(timedelta(hours=2)))

    assert share_link_repository.consume(links[0].id, just_before) is True


def test_purge_expired_deletes_only_expired_links(share_link_repository: SqlShareLinkRepository, session: Session):
    fresh = _links("s1", 1, now=NOW)
    stale = [
        ShareLink.create(
            setup_id="s1",
            share_index=2,
            lookup_hash=_lookup("stale"),
            sealed_share="sealed-stale",
            now=NOW - timedelta(hours=49),
        )
    ]
    share_link_repository.replace_all(fresh + stale)

    share_link_repository.purge_expired(NOW)

    assert [row.share_index for row in _stored_rows(session)] == [1]
