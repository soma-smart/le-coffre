"""A setup that fails half way leaves no trace: not in the database, not in memory.

Runs CreateVaultUseCase against SQLite with the real adapters, all on one
session as in a request, and makes the share links write fail for real after
the vault row has been written.
"""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from shared_kernel.adapters.secondary.sql import SqlTransactionGateway
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from tests.shared_kernel.fakes import FakeTimeGateway
from vault_management_context.adapters.secondary import (
    AesEncryptionGateway,
    AesGcmShareSealingGateway,
    CryptoShamirGateway,
    InMemoryVaultSessionGateway,
    SqlShareLinkRepository,
    SqlVaultEventRepository,
    SqlVaultRepository,
)
from vault_management_context.adapters.secondary.sql import VaultEventTable, VaultShareLinkTable, VaultTable
from vault_management_context.application.commands import CreateVaultCommand
from vault_management_context.application.use_cases import CreateVaultUseCase
from vault_management_context.domain.entities import ShareLink
from vault_management_context.domain.events import VaultCreatedEvent

NOW = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


class _BrokenShareLinkRepository(SqlShareLinkRepository):
    """Writes one link twice once armed: the unique lookup hash makes the database refuse the batch."""

    def __init__(self, session: Session):
        super().__init__(session)
        self.armed = False

    def replace_all(self, links: list[ShareLink]) -> None:
        if self.armed:
            links = [*links, replace(links[0], id=uuid4())]
        super().replace_all(links)


@pytest.fixture
def share_link_repository(session):
    return _BrokenShareLinkRepository(session)


@pytest.fixture
def vault_session_gateway():
    return InMemoryVaultSessionGateway()


@pytest.fixture
def event_publisher():
    return FakeDomainEventPublisher()


@pytest.fixture
def use_case(session, share_link_repository, vault_session_gateway, event_publisher):
    return CreateVaultUseCase(
        SqlVaultRepository(session),
        CryptoShamirGateway(),
        AesEncryptionGateway(),
        vault_session_gateway,
        event_publisher,
        SqlVaultEventRepository(session),
        share_link_repository,
        AesGcmShareSealingGateway(),
        FakeTimeGateway(NOW),
        SqlTransactionGateway(session),
    )


def _rows(session: Session, table) -> list:
    session.expire_all()
    return list(session.exec(select(table)).all())


def test_a_setup_whose_links_fail_to_write_leaves_nothing_behind(
    use_case, session, share_link_repository, vault_session_gateway, event_publisher
):
    share_link_repository.armed = True

    with pytest.raises(IntegrityError):
        use_case.execute(CreateVaultCommand(nb_shares=3, threshold=2, setup_id=uuid4()))

    # The vault row was written before the links: it went with them.
    assert _rows(session, VaultTable) == []
    assert _rows(session, VaultShareLinkTable) == []
    assert _rows(session, VaultEventTable) == []
    assert vault_session_gateway.is_vault_locked()
    assert event_publisher.get_published_events_of_type(VaultCreatedEvent) == []


def test_a_re_setup_whose_links_fail_to_write_keeps_the_previous_setup_whole(
    use_case, session, share_link_repository, vault_session_gateway, event_publisher
):
    first_setup_id = uuid4()
    first = use_case.execute(CreateVaultCommand(nb_shares=3, threshold=2, setup_id=first_setup_id))
    first_vault = _rows(session, VaultTable)[0]
    first_encrypted_key = first_vault.encrypted_key
    first_lookup_hashes = {row.lookup_hash for row in _rows(session, VaultShareLinkTable)}
    first_key_in_memory = vault_session_gateway.get_decrypted_key()

    share_link_repository.armed = True
    with pytest.raises(IntegrityError):
        use_case.execute(CreateVaultCommand(nb_shares=2, threshold=2, setup_id=uuid4()))

    # Vault row, links and audit all still those of the first setup, whose
    # links' DELETE by replace_all was rolled back too.
    vaults = _rows(session, VaultTable)
    assert [(vault.setup_id, vault.encrypted_key) for vault in vaults] == [(str(first_setup_id), first_encrypted_key)]
    assert {row.lookup_hash for row in _rows(session, VaultShareLinkTable)} == first_lookup_hashes
    assert len(first.share_links) == 3
    assert [event.event_type for event in _rows(session, VaultEventTable)] == ["VaultCreatedEvent"]
    # The key in memory still matches the vault in the database
    assert vault_session_gateway.get_decrypted_key() == first_key_in_memory
    assert len(event_publisher.get_published_events_of_type(VaultCreatedEvent)) == 1
