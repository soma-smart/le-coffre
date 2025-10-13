import pytest

from vault_management_context.domain.entities import Vault
from vault_management_context.application.use_cases import (
    GetVaultStatusUseCase,
)
from vault_management_context.application.responses.vault_status import VaultStatus


@pytest.fixture()
def use_case(vault_repository, vault_session_gateway):
    return GetVaultStatusUseCase(vault_repository, vault_session_gateway)


def test_should_return_not_setup_when_no_vault(use_case):
    status = use_case.execute()
    assert status.name == "NOT_SETUP"


def test_should_return_locked_when_vault_is_locked(
    use_case, vault_repository, vault_session_gateway
):
    vault_repository.save(Vault(
        nb_shares=3, 
        threshold=2, 
        encrypted_key="encrypted_vault_key_hex",
        setup_id="test-setup-id",
        status=VaultStatus.SETUPED.value  # Vault is completed, not pending
    ))
    vault_session_gateway.clear_decrypted_key()

    status = use_case.execute()

    assert status.name == "LOCKED"


def test_should_return_unlocked_when_vault_is_unlocked(
    use_case, vault_repository, vault_session_gateway
):
    vault_repository.save(Vault(
        nb_shares=3, 
        threshold=2, 
        encrypted_key="encrypted_vault_key_hex",
        setup_id="test-setup-id",
        status=VaultStatus.SETUPED.value  # Vault is completed, not pending
    ))
    vault_session_gateway.store_decrypted_key("decrypted_vault_key")

    status = use_case.execute()

    assert status.name == "UNLOCKED"


def test_should_return_unlocked_when_vault_is_pending_with_session(
    use_case, vault_repository, vault_session_gateway
):
    vault_repository.save(Vault(
        nb_shares=3, 
        threshold=2, 
        encrypted_key="encrypted_vault_key_hex",
        status=VaultStatus.PENDING.value,
        setup_id="test-setup-id"
    ))
    vault_session_gateway.store_decrypted_key("decrypted_vault_key")

    status = use_case.execute()

    assert status.name == "UNLOCKED"
