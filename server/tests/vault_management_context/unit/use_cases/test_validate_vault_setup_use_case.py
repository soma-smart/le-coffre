import pytest

from vault_management_context.domain.entities import Vault
from vault_management_context.application.use_cases import ValidateVaultSetupUseCase
from vault_management_context.application.use_cases.validate_vault_setup_use_case import VaultSetupValidationError


@pytest.fixture()
def use_case(vault_repository):
    return ValidateVaultSetupUseCase(vault_repository)


def test_should_validate_setup_with_correct_setup_id(use_case, vault_repository):
    setup_id = "test-setup-id-123"
    vault = Vault(
        nb_shares=3,
        threshold=2,
        encrypted_key="encrypted_key",
        setup_id=setup_id,
        status="PENDING"
    )
    vault_repository.save(vault)

    # Should not raise any exception
    use_case.execute(setup_id)

    # Verify vault status is updated
    stored_vault = vault_repository.get()
    assert stored_vault.status == "SETUPED"


def test_should_fail_when_no_vault_exists(use_case):
    with pytest.raises(VaultSetupValidationError) as exc_info:
        use_case.execute("any-setup-id")

    assert str(exc_info.value) == "No vault found"


def test_should_fail_when_vault_not_in_pending_state(use_case, vault_repository):
    setup_id = "test-setup-id-123"
    vault = Vault(
        nb_shares=3,
        threshold=2,
        encrypted_key="encrypted_key",
        setup_id=setup_id,
        status="SETUPED"  # Already completed
    )
    vault_repository.save(vault)

    with pytest.raises(VaultSetupValidationError) as exc_info:
        use_case.execute(setup_id)

    assert str(exc_info.value) == "Vault is not in pending state"


def test_should_fail_when_setup_id_does_not_match(use_case, vault_repository):
    vault = Vault(
        nb_shares=3,
        threshold=2,
        encrypted_key="encrypted_key",
        setup_id="correct-setup-id",
        status="PENDING"
    )
    vault_repository.save(vault)

    with pytest.raises(VaultSetupValidationError) as exc_info:
        use_case.execute("wrong-setup-id")

    assert str(exc_info.value) == "Invalid setup ID"