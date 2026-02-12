import pytest
from uuid import UUID

from vault_management_context.application.commands import LockVaultCommand
from vault_management_context.domain.exceptions import (
    VaultNotSetupException,
    VaultLockedException,
)
from vault_management_context.application.use_cases import (
    LockVaultUseCase,
)
from shared_kernel.domain.entities import AuthenticatedUser
from shared_kernel.adapters.primary.exceptions import NotAdminError
from vault_management_context.domain.events import VaultLockedEvent
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from ..fakes import FakeVaultRepository, FakeVaultSessionGateway


@pytest.fixture()
def use_case(
    vault_repository: FakeVaultRepository,
    vault_session_gateway: FakeVaultSessionGateway,
    event_publisher,
):
    return LockVaultUseCase(vault_repository, vault_session_gateway, event_publisher)


def test_given_unlocked_vault_when_locking_vault_should_clear_session_key(
    use_case,
    vault_repository: FakeVaultRepository,
    vault_session_gateway: FakeVaultSessionGateway,
):
    admin_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"]
    )
    vault_repository.save_vault_with_shares(
        nb_shares=3, threshold=2, encrypted_key="encrypted_vault_key_hex"
    )
    vault_session_gateway.store_decrypted_key("decrypted_vault_key")

    command = LockVaultCommand(requesting_user=admin_user)
    use_case.execute(command)

    with pytest.raises(ValueError):
        vault_session_gateway.get_decrypted_key()


def test_given_locked_vault_when_locking_vault_should_raise_vault_locked_exception(
    use_case, vault_repository: FakeVaultRepository
):
    admin_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"]
    )
    vault_repository.save_vault_with_shares(
        nb_shares=3, threshold=2, encrypted_key="encrypted_vault_key_hex"
    )

    command = LockVaultCommand(requesting_user=admin_user)
    with pytest.raises(VaultLockedException):
        use_case.execute(command)


def test_given_vault_not_setup_when_locking_vault_should_raise_vault_not_setup_exception(
    use_case,
):
    admin_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"]
    )

    command = LockVaultCommand(requesting_user=admin_user)
    with pytest.raises(VaultNotSetupException):
        use_case.execute(command)


def test_given_non_admin_user_when_locking_vault_should_raise_not_admin_error(
    use_case,
    vault_repository: FakeVaultRepository,
    vault_session_gateway: FakeVaultSessionGateway,
):
    regular_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6"), roles=[]
    )
    vault_repository.save_vault_with_shares(
        nb_shares=3, threshold=2, encrypted_key="encrypted_vault_key_hex"
    )
    vault_session_gateway.store_decrypted_key("decrypted_vault_key")

    command = LockVaultCommand(requesting_user=regular_user)
    with pytest.raises(NotAdminError):
        use_case.execute(command)


def test_given_unlocked_vault_when_locking_vault_should_publish_vault_locked_event(
    use_case,
    vault_repository: FakeVaultRepository,
    vault_session_gateway: FakeVaultSessionGateway,
    event_publisher: FakeDomainEventPublisher,
):
    admin_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"]
    )
    vault_repository.save_vault_with_shares(
        nb_shares=3, threshold=2, encrypted_key="encrypted_vault_key_hex"
    )
    vault_session_gateway.store_decrypted_key("decrypted_vault_key")

    command = LockVaultCommand(requesting_user=admin_user)
    use_case.execute(command)

    events = event_publisher.get_published_events_of_type(VaultLockedEvent)
    assert len(events) == 1
    assert events[0].locked_by_user_id == UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
