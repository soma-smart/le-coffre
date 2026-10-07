import hashlib
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from shared_kernel.adapters.secondary.sql import SqlTransactionGateway
from vault_management_context.adapters.secondary import SqlShareLinkRepository, SqlVaultRepository
from vault_management_context.adapters.secondary.sql import VaultShareLinkTable
from vault_management_context.application.responses import VaultStatus
from vault_management_context.domain.entities import ShareLink, Vault

NOW = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


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


def _stored_rows(session: Session) -> list[VaultShareLinkTable]:
    session.expire_all()
    return list(session.exec(select(VaultShareLinkTable)).all())


# Behaviour shared with the fake lives in test_share_link_repository_contract.py;
# what is left here is specific to SQL: time zones, sessions, transactions.


def test_replace_all_then_get_by_lookup_hash_round_trips_the_link(share_link_repository: SqlShareLinkRepository):
    links = _links("s1", 3)
    share_link_repository.replace_all(links)

    stored = share_link_repository.get_by_lookup_hash(_lookup("s1-2"))

    assert stored == links[1]
    # Datetimes come back aware, so they compare with what TimeGateway hands out.
    assert stored is not None and stored.expires_at.tzinfo is not None


def _deliver(repository: SqlShareLinkRepository, link: ShareLink, at: datetime):
    return repository.deliver(link.id, at, link.reopen_deadline(at))


def test_delivery_compares_expiry_in_utc_whatever_the_caller_offset(share_link_repository: SqlShareLinkRepository):
    link = _links("s1", 1)[0]
    share_link_repository.replace_all([link])
    # One minute before expiry, expressed at UTC+2: still valid.
    just_before = (link.expires_at - timedelta(minutes=1)).astimezone(timezone(timedelta(hours=2)))

    assert _deliver(share_link_repository, link, just_before) is not None


def test_a_concurrent_first_delivery_turns_ours_into_a_reopening(tmp_path):
    # Two sessions on a file database, like two requests: ours loaded the link
    # before the other one delivered it.
    engine = create_engine(f"sqlite:///{tmp_path / 'race.sqlite'}")
    SQLModel.metadata.create_all(engine)
    link = _links("s1", 1)[0]
    with Session(engine) as setup:
        SqlShareLinkRepository(setup).replace_all([link])
    first, ours = NOW + timedelta(hours=1), NOW + timedelta(hours=1, minutes=1)

    with Session(engine, expire_on_commit=False) as our_session, Session(engine) as other_session:
        repository = SqlShareLinkRepository(our_session)
        assert repository.get_by_lookup_hash(link.lookup_hash).delivered_at is None  # type: ignore[union-attr]
        our_session.commit()  # end the read, as SQLite would otherwise lock the other writer out
        _deliver(SqlShareLinkRepository(other_session), link, first)

        delivery = _deliver(repository, link, ours)

    assert delivery is not None
    assert (delivery.first_delivered_at, delivery.reopened) == (first, True)
    engine.dispose()


def _pending_vault(setup_id: str) -> Vault:
    return Vault(
        nb_shares=3, threshold=2, encrypted_key=f"key-{setup_id}", setup_id=setup_id, status=VaultStatus.PENDING.value
    )


def test_a_failed_setup_leaves_neither_the_vault_nor_its_links(
    session: Session, vault_repository: SqlVaultRepository, share_link_repository: SqlShareLinkRepository
):
    with pytest.raises(RuntimeError), SqlTransactionGateway(session).atomic():
        vault_repository.save(_pending_vault("s1"))
        share_link_repository.replace_all(_links("s1", 3))
        raise RuntimeError("audit event failed")

    assert vault_repository.get() is None
    assert _stored_rows(session) == []


def test_a_failed_re_setup_keeps_the_previous_setup_whole(
    session: Session, vault_repository: SqlVaultRepository, share_link_repository: SqlShareLinkRepository
):
    with SqlTransactionGateway(session).atomic():
        vault_repository.save(_pending_vault("s1"))
        share_link_repository.replace_all(_links("s1", 3))

    with pytest.raises(RuntimeError), SqlTransactionGateway(session).atomic():
        vault_repository.save(_pending_vault("s2"))
        share_link_repository.replace_all(_links("s2", 2))
        raise RuntimeError("audit event failed")

    vault = vault_repository.get()
    assert vault is not None
    assert vault.setup_id == "s1"
    assert {row.setup_id for row in _stored_rows(session)} == {"s1"}
    assert len(_stored_rows(session)) == 3


def test_delivery_inside_an_atomic_block_is_undone_when_the_block_fails(
    session: Session, share_link_repository: SqlShareLinkRepository
):
    link = _links("s1", 1)[0]
    share_link_repository.replace_all([link])

    with pytest.raises(RuntimeError), SqlTransactionGateway(session).atomic():
        assert _deliver(share_link_repository, link, NOW) is not None
        raise RuntimeError("audit event failed")

    stored = share_link_repository.get_by_lookup_hash(link.lookup_hash)
    assert stored is not None and stored.delivered_at is None


def test_removal_inside_an_atomic_block_is_undone_when_the_block_fails(
    session: Session, share_link_repository: SqlShareLinkRepository
):
    link = _links("s1", 1)[0]
    share_link_repository.replace_all([link])
    _deliver(share_link_repository, link, NOW)

    with pytest.raises(RuntimeError), SqlTransactionGateway(session).atomic():
        assert share_link_repository.remove_delivered(link.id, NOW)
        raise RuntimeError("audit event failed")

    assert share_link_repository.get_by_lookup_hash(link.lookup_hash) is not None
