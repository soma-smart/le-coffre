import pytest

from vault_management_context.application.commands import ValidateVaultSetupCommand
from vault_management_context.domain.entities import Vault
from vault_management_context.application.use_cases import ValidateVaultSetupUseCase
from vault_management_context.domain.exceptions import (
    NoVaultExisting,
    VaultAlreadySetuped,
    VaultSetupIdNotFound,
)
from vault_management_context.application.responses import VaultStatus
from ..fakes import FakeVaultRepository


@pytest.fixture()
def use_case(vault_repository: FakeVaultRepository):
    return ValidateVaultSetupUseCase(vault_repository)


def test_given_pending_vault_with_correct_setup_id_when_validating_should_update_status_to_setuped(
    use_case, vault_repository: FakeVaultRepository
):
    setup_id = "test-setup-id-123"
    vault = Vault(
        nb_shares=3,
        threshold=2,
        encrypted_key="encrypted_key",
        setup_id=setup_id,
        status=VaultStatus.PENDING.value,
    )
    vault_repository.save(vault)

    # Should not raise any exception
    command = ValidateVaultSetupCommand(setup_id=setup_id)
    use_case.execute(command)

    # Verify vault status is updated
    stored_vault = vault_repository.get()

    assert stored_vault
    assert stored_vault.status == VaultStatus.SETUPED.value


def test_given_no_vault_exists_when_validating_setup_should_raise_no_vault_existing_error(
    use_case,
):
    command = ValidateVaultSetupCommand(setup_id="any-setup-id")
    with pytest.raises(NoVaultExisting) as exc_info:
        use_case.execute(command)

    assert str(exc_info.value) == "No vault found"


def test_given_vault_already_setuped_when_validating_setup_should_raise_vault_already_setuped_error(
    use_case, vault_repository: FakeVaultRepository
):
    setup_id = "test-setup-id-123"
    vault = Vault(
        nb_shares=3,
        threshold=2,
        encrypted_key="encrypted_key",
        setup_id=setup_id,
        status=VaultStatus.SETUPED.value,  # Already completed
    )
    vault_repository.save(vault)

    command = ValidateVaultSetupCommand(setup_id=setup_id)
    with pytest.raises(VaultAlreadySetuped) as exc_info:
        use_case.execute(command)

    assert str(exc_info.value) == "Vault is not in pending state"


def test_given_wrong_setup_id_when_validating_setup_should_raise_vault_setup_id_not_found_error(
    use_case, vault_repository: FakeVaultRepository
):
    vault = Vault(
        nb_shares=3,
        threshold=2,
        encrypted_key="encrypted_key",
        setup_id="correct-setup-id",
        status=VaultStatus.PENDING.value,
    )
    vault_repository.save(vault)

    command = ValidateVaultSetupCommand(setup_id="wrong-setup-id")
    with pytest.raises(VaultSetupIdNotFound) as exc_info:
        use_case.execute(command)

    assert str(exc_info.value) == "Invalid setup ID"
