import pytest
from uuid import UUID

from vault_management_context.application.responses.vault_status import VaultStatus
from vault_management_context.domain.entities import Share, Vault
from vault_management_context.domain.value_objects import ShamirResult
from vault_management_context.domain.exceptions import (
    VaultNotSetupException,
    ShareReconstructionError,
    VaultUnlockedError,
)
from vault_management_context.application.use_cases.unlock_vault_use_case import (
    UnlockVaultUseCase,
)
from identity_access_management_context.adapters.primary.dependencies import (
    AuthenticatedUser,
    NotAdminError,
)


@pytest.fixture()
def use_case(
    vault_repository, shamir_gateway, encryption_gateway, vault_session_gateway
):
    return UnlockVaultUseCase(
        vault_repository, shamir_gateway, encryption_gateway, vault_session_gateway
    )


def test_should_unlock_vault_with_valid_shares_and_decrypt_key(
    use_case,
    vault_repository,
    shamir_gateway,
    encryption_gateway,
    vault_session_gateway,
):
    admin_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"]
    )
    vault_key = "test_vault_key_12345678"
    master_key = "master_key"
    encrypted_key = "encrypted_vault_key_hex"
    shares = [Share(0, "share0"), Share(1, "share1")]

    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key=encrypted_key,
            setup_id="test-setup-id",
            status=VaultStatus.SETUPED.value,
        )
    )

    shamir_gateway.set_shamir_result(ShamirResult(shares, master_key))
    encryption_gateway.set_decrypted_data(vault_key)
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)

    use_case.execute(shares, admin_user)

    # Verify the decrypted key is now in session
    decrypted_key = vault_session_gateway.get_decrypted_key()
    assert decrypted_key == vault_key


def test_should_fail_when_vault_is_not_setup(use_case):
    admin_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"]
    )
    shares = [Share(0, "share0"), Share(1, "share1")]

    with pytest.raises(VaultNotSetupException):
        use_case.execute(shares, admin_user)


def test_should_fail_when_not_enough_shares_provided(use_case, vault_repository):
    admin_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"]
    )
    vault_repository.save_vault_with_shares(nb_shares=3, threshold=2)
    shares = [Share(0, "share0")]

    with pytest.raises(ShareReconstructionError):
        use_case.execute(shares, admin_user)


def test_should_fail_when_shamir_reconstruction_fails(
    use_case, vault_repository, shamir_gateway
):
    admin_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"]
    )
    encrypted_key = "encrypted_vault_key_hex"
    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key=encrypted_key,
            setup_id="test-setup-id",
            status=VaultStatus.SETUPED.value,
        )
    )

    shares = [Share(0, "share0"), Share(1, "share1")]
    master_secret = "master_secret"
    shamir_gateway.set_shamir_result(ShamirResult(shares, master_secret))

    invalid_shares = [Share(0, "invalid_share0"), Share(1, "invalid_share1")]

    with pytest.raises(ShareReconstructionError):
        use_case.execute(invalid_shares, admin_user)


def test_should_fail_when_vault_is_already_unlock(
    use_case, vault_repository, shamir_gateway, encryption_gateway
):
    admin_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"]
    )
    encrypted_key = "encrypted_vault_key_hex"
    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key=encrypted_key,
            setup_id="test-setup-id",
            status=VaultStatus.SETUPED.value,
        )
    )

    shares = [Share(0, "share0"), Share(1, "share1")]
    master_key = "master_key"
    shamir_gateway.set_shamir_result(ShamirResult(shares, master_key))

    vault_key = "test_vault_key_12345678"
    encryption_gateway.set_decrypted_data(vault_key)
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)

    use_case.execute(shares, admin_user)

    with pytest.raises(VaultUnlockedError):
        use_case.execute(shares, admin_user)


def test_should_raise_not_admin_error_when_requesting_user_is_not_admin(
    use_case, vault_repository, shamir_gateway, encryption_gateway
):
    regular_user = AuthenticatedUser(
        user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6"), roles=[]
    )
    encrypted_key = "encrypted_vault_key_hex"
    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key=encrypted_key,
            setup_id="test-setup-id",
            status=VaultStatus.SETUPED.value,
        )
    )

    shares = [Share(0, "share0"), Share(1, "share1")]
    master_key = "master_key"
    shamir_gateway.set_shamir_result(ShamirResult(shares, master_key))

    vault_key = "test_vault_key_12345678"
    encryption_gateway.set_decrypted_data(vault_key)
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)

    with pytest.raises(NotAdminError):
        use_case.execute(shares, regular_user)
