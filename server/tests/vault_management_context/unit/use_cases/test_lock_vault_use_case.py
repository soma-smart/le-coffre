import pytest

from vault_management_context.domain.exceptions import (
    VaultNotSetupException,
    VaultLockedException,
)
from vault_management_context.application.use_cases.lock_vault_use_case import (
    LockVaultUseCase,
)


@pytest.fixture()
def use_case(vault_repository, vault_session_gateway):
    return LockVaultUseCase(vault_repository, vault_session_gateway)


def test_should_lock_vault(use_case, vault_repository, vault_session_gateway):
    vault_repository.save_vault_with_shares(
        nb_shares=3, threshold=2, encrypted_key="encrypted_vault_key_hex"
    )
    vault_session_gateway.store_decrypted_key("decrypted_vault_key")

    use_case.execute()

    with pytest.raises(ValueError):
        vault_session_gateway.get_decrypted_key()


def test_should_not_lock_vault_if_not_unlocked(use_case, vault_repository):
    vault_repository.save_vault_with_shares(
        nb_shares=3, threshold=2, encrypted_key="encrypted_vault_key_hex"
    )

    with pytest.raises(VaultLockedException):
        use_case.execute()


def test_when_not_setup_should_lock_fail(use_case):
    with pytest.raises(VaultNotSetupException):
        use_case.execute()
