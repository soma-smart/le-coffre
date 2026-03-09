import pytest

from vault_management_context.application.commands import GetVaultStatusCommand
from vault_management_context.application.responses import VaultStatus
from vault_management_context.application.use_cases import (
    GetVaultStatusUseCase,
)
from vault_management_context.domain.entities import Share, Vault

from ..fakes import FakeShareRepository, FakeVaultRepository, FakeVaultSessionGateway


@pytest.fixture()
def use_case(
    vault_repository: FakeVaultRepository,
    vault_session_gateway: FakeVaultSessionGateway,
    share_repository: FakeShareRepository,
):
    return GetVaultStatusUseCase(vault_repository, vault_session_gateway, share_repository)


def test_given_no_vault_exists_when_getting_vault_status_should_return_not_setup(
    use_case,
):
    command = GetVaultStatusCommand()
    status = use_case.execute(command)
    assert status.name == "NOT_SETUP"


def test_given_setuped_vault_without_session_when_getting_vault_status_should_return_locked(
    use_case,
    vault_repository: FakeVaultRepository,
    vault_session_gateway: FakeVaultSessionGateway,
):
    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key="encrypted_vault_key_hex",
            setup_id="test-setup-id",
            status=VaultStatus.SETUPED.value,  # Vault is completed, not pending
        )
    )
    vault_session_gateway.clear_decrypted_key()

    command = GetVaultStatusCommand()
    status = use_case.execute(command)

    assert status.name == "LOCKED"


def test_given_setuped_vault_with_session_when_getting_vault_status_should_return_unlocked(
    use_case,
    vault_repository: FakeVaultRepository,
    vault_session_gateway: FakeVaultSessionGateway,
):
    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key="encrypted_vault_key_hex",
            setup_id="test-setup-id",
            status=VaultStatus.SETUPED.value,  # Vault is completed, not pending
        )
    )
    vault_session_gateway.store_decrypted_key("decrypted_vault_key")

    command = GetVaultStatusCommand()
    status = use_case.execute(command)

    assert status.name == "UNLOCKED"


def test_given_pending_vault_with_session_when_getting_vault_status_should_return_unlocked(
    use_case,
    vault_repository: FakeVaultRepository,
    vault_session_gateway: FakeVaultSessionGateway,
):
    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key="encrypted_vault_key_hex",
            status=VaultStatus.PENDING.value,
            setup_id="test-setup-id",
        )
    )
    vault_session_gateway.store_decrypted_key("decrypted_vault_key")

    command = GetVaultStatusCommand()
    status = use_case.execute(command)

    assert status.name == "UNLOCKED"


def test_given_setuped_vault_without_session_and_shares_exist_when_getting_vault_status_should_return_pending_unlock(
    use_case,
    vault_repository: FakeVaultRepository,
    vault_session_gateway: FakeVaultSessionGateway,
    share_repository: FakeShareRepository,
):
    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key="encrypted_vault_key_hex",
            setup_id="test-setup-id",
            status=VaultStatus.SETUPED.value,
        )
    )
    vault_session_gateway.clear_decrypted_key()
    share_repository.add([Share(secret="share1"), Share(secret="share2")])

    command = GetVaultStatusCommand()
    status = use_case.execute(command)

    assert status.name == "PENDING_UNLOCK"
