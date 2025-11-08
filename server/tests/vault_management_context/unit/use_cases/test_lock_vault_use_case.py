import pytest
from uuid import UUID

from vault_management_context.domain.exceptions import (
    VaultNotSetupException,
    VaultLockedException,
)
from vault_management_context.application.use_cases.lock_vault_use_case import (
    LockVaultUseCase,
)
from identity_access_management_context.adapters.primary.dependencies import (
    AuthenticatedUser,
    NotAdminError,
)


@pytest.fixture()
def use_case(vault_repository, vault_session_gateway):
    return LockVaultUseCase(vault_repository, vault_session_gateway)


def test_should_lock_vault(use_case, vault_repository, vault_session_gateway):
    admin_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"]
    )
    vault_repository.save_vault_with_shares(
        nb_shares=3, threshold=2, encrypted_key="encrypted_vault_key_hex"
    )
    vault_session_gateway.store_decrypted_key("decrypted_vault_key")

    use_case.execute(admin_user)

    with pytest.raises(ValueError):
        vault_session_gateway.get_decrypted_key()


def test_should_not_lock_vault_if_not_unlocked(use_case, vault_repository):
    admin_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"]
    )
    vault_repository.save_vault_with_shares(
        nb_shares=3, threshold=2, encrypted_key="encrypted_vault_key_hex"
    )

    with pytest.raises(VaultLockedException):
        use_case.execute(admin_user)


def test_when_not_setup_should_lock_fail(use_case):
    admin_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"]
    )

    with pytest.raises(VaultNotSetupException):
        use_case.execute(admin_user)


def test_should_raise_not_admin_error_when_requesting_user_is_not_admin(
    use_case, vault_repository, vault_session_gateway
):
    regular_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6"), roles=[]
    )
    vault_repository.save_vault_with_shares(
        nb_shares=3, threshold=2, encrypted_key="encrypted_vault_key_hex"
    )
    vault_session_gateway.store_decrypted_key("decrypted_vault_key")

    with pytest.raises(NotAdminError):
        use_case.execute(regular_user)
