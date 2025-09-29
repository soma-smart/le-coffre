import pytest

from vault_management_context.application.use_cases import (
    GetVaultStatusUseCase,
)


@pytest.fixture()
def use_case(vault_repository, vault_session_gateway):
    return GetVaultStatusUseCase(vault_repository, vault_session_gateway)


def test_should_return_not_setup_when_no_vault(use_case):
    status = use_case.execute()
    assert status.name == "NOT_SETUP"


def test_should_return_locked_when_vault_is_locked(
    use_case, vault_repository, vault_session_gateway
):
    vault_repository.save_vault_with_shares(
        nb_shares=3, threshold=2, encrypted_key="encrypted_vault_key_hex"
    )
    vault_session_gateway.clear_decrypted_key()

    status = use_case.execute()

    assert status.name == "LOCKED"


def test_should_return_unlocked_when_vault_is_unlocked(
    use_case, vault_repository, vault_session_gateway
):
    vault_repository.save_vault_with_shares(
        nb_shares=3, threshold=2, encrypted_key="encrypted_vault_key_hex"
    )
    vault_session_gateway.store_decrypted_key("decrypted_vault_key")

    status = use_case.execute()

    assert status.name == "UNLOCKED"
