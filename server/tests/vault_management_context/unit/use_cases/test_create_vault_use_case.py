import pytest

from vault_management_context.domain.entities import Vault, Share
from vault_management_context.domain.exceptions import (
    VaultAlreadyExistsError,
    InvalidShareCountError,
    InvalidThresholdError,
    ThresholdExceedsShareCountError,
)
from vault_management_context.application.use_cases import (
    CreateVaultUseCase,
)
from vault_management_context.domain.value_objects.shamir_result import ShamirResult


@pytest.fixture()
def use_case(
    vault_repository, shamir_gateway, encryption_gateway, vault_session_gateway
):
    return CreateVaultUseCase(
        vault_repository, shamir_gateway, encryption_gateway, vault_session_gateway
    )


def test_should_create_shares_and_store_encrypted_key(
    use_case,
    vault_repository,
    shamir_gateway,
    encryption_gateway,
    vault_session_gateway,
):
    expected_shares = [
        Share(0, "1"),
        Share(1, "2"),
        Share(2, "3"),
        Share(3, "4"),
        Share(4, "5"),
    ]
    master_key = "master_secret_from_shamir"
    encrypted_key = "encrypted_vault_key_123"
    decrypted_key = "generated_vault_key"

    shamir_result = ShamirResult(shares=expected_shares, master_key=master_key)
    shamir_gateway.set_shamir_result(shamir_result)

    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_decrypted_data(decrypted_key)
    encryption_gateway.set_master_key(master_key)

    shares = use_case.execute(5, 3)

    assert shares == expected_shares
    stored_vault = vault_repository.get()
    assert stored_vault.nb_shares == 5
    assert stored_vault.threshold == 3
    assert stored_vault.encrypted_key == encrypted_key

    # Verify the decrypted key is stored in the session
    assert vault_session_gateway.get_decrypted_key() == decrypted_key


def test_should_fail_when_vault_is_already_created(use_case, vault_repository):
    vault_repository.save(Vault(nb_shares=5, threshold=3, encrypted_key="test"))

    with pytest.raises(VaultAlreadyExistsError) as exc_info:
        use_case.execute(5, 3)

    assert (
        str(exc_info.value) == "A vault has already been created for this organization"
    )


def test_should_fail_when_nb_shares_is_less_than_2(use_case):
    with pytest.raises(InvalidShareCountError) as exc_info:
        use_case.execute(1, 2)

    assert (
        str(exc_info.value)
        == "Share count must be at least 2 for security reasons, got 1"
    )


def test_should_fail_when_threshold_is_less_than_2(use_case):
    with pytest.raises(InvalidThresholdError) as exc_info:
        use_case.execute(3, 1)

    assert (
        str(exc_info.value) == "Threshold must be at least 2 to ensure security, got 1"
    )


def test_should_fail_when_threshold_is_greater_than_nb_shares(use_case):
    with pytest.raises(ThresholdExceedsShareCountError) as exc_info:
        use_case.execute(3, 4)

    expected_message = (
        "Threshold 4 cannot exceed share count 3 - impossible to unlock vault"
    )
    assert str(exc_info.value) == expected_message
