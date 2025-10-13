import pytest
from uuid import uuid4

from vault_management_context.domain.entities import Vault, Share
from vault_management_context.application.responses.vault_status import VaultStatus
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
    setup_id = uuid4()

    shamir_result = ShamirResult(shares=expected_shares, master_key=master_key)
    shamir_gateway.set_shamir_result(shamir_result)

    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)
    encryption_gateway.set_decrypted_data("decrypted_vault_key")  # For decrypt_and_store_key

    result = use_case.execute(5, 3, setup_id)

    # Check that result is VaultSetupResponse with setup_id and shares
    assert result.shares == expected_shares
    assert result.setup_id == str(setup_id)
    
    stored_vault = vault_repository.get()
    assert stored_vault.nb_shares == 5
    assert stored_vault.threshold == 3
    assert stored_vault.encrypted_key == encrypted_key
    assert stored_vault.status == VaultStatus.PENDING.value
    assert stored_vault.setup_id == str(setup_id)


def test_should_fail_when_vault_is_already_created(use_case, vault_repository):
    # Create a vault that is already validated (not in PENDING state)
    vault_repository.save(Vault(nb_shares=5, threshold=3, encrypted_key="test", setup_id=str(uuid4()), status=VaultStatus.SETUPED.value))

    with pytest.raises(VaultAlreadyExistsError) as exc_info:
        use_case.execute(5, 3, uuid4())

    assert (
        str(exc_info.value) == "A vault has already been created for this organization"
    )


def test_should_allow_re_setup_when_vault_is_pending(use_case, vault_repository, shamir_gateway, encryption_gateway):
    # Create a vault in PENDING state
    vault_repository.save(Vault(nb_shares=3, threshold=2, encrypted_key="test", status=VaultStatus.PENDING.value, setup_id=str(uuid4())))

    expected_shares = [Share(0, "1"), Share(1, "2")]
    master_key = "master_secret_from_shamir"
    encrypted_key = "encrypted_vault_key_123"
    new_setup_id = uuid4()

    shamir_result = ShamirResult(shares=expected_shares, master_key=master_key)
    shamir_gateway.set_shamir_result(shamir_result)
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)
    encryption_gateway.set_decrypted_data("decrypted_vault_key")  # For decrypt_and_store_key

    # Should be able to re-setup
    result = use_case.execute(2, 2, new_setup_id)
    assert result.shares == expected_shares
    assert result.setup_id == str(new_setup_id)


def test_should_fail_when_nb_shares_is_less_than_2(use_case):
    with pytest.raises(InvalidShareCountError) as exc_info:
        use_case.execute(1, 2, uuid4())

    assert (
        str(exc_info.value)
        == "Share count must be at least 2 for security reasons, got 1"
    )


def test_should_fail_when_threshold_is_less_than_2(use_case):
    with pytest.raises(InvalidThresholdError) as exc_info:
        use_case.execute(3, 1, uuid4())

    assert (
        str(exc_info.value) == "Threshold must be at least 2 to ensure security, got 1"
    )


def test_should_fail_when_threshold_is_greater_than_nb_shares(use_case):
    with pytest.raises(ThresholdExceedsShareCountError) as exc_info:
        use_case.execute(3, 4, uuid4())

    expected_message = (
        "Threshold 4 cannot exceed share count 3 - impossible to unlock vault"
    )
    assert str(exc_info.value) == expected_message
