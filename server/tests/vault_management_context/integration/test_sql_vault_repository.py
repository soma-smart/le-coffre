from vault_management_context.domain.entities.vault import Vault
from vault_management_context.application.responses import VaultStatus


def test_should_return_none_when_no_vault_exists(vault_repository):
    result = vault_repository.get()
    assert result is None


def test_should_retrieve_vault_when_vault_exists(vault_repository):
    vault = Vault(
        nb_shares=2,
        threshold=2,
        encrypted_key="encrypted_key",
        setup_id="test-setup-id",
        status=VaultStatus.SETUPED.value,
    )

    vault_repository.save(vault)
    assert vault_repository.get() == vault


def test_should_update_vault_when_saving_again(vault_repository):
    vault = Vault(
        nb_shares=2,
        threshold=2,
        encrypted_key="encrypted_key",
        setup_id="test-setup-id",
        status=VaultStatus.SETUPED.value,
    )
    vault_repository.save(vault)

    updated_vault = Vault(
        nb_shares=2,
        threshold=2,
        encrypted_key="new_encrypted_key",
        setup_id="test-setup-id",
        status=VaultStatus.SETUPED.value,
    )
    vault_repository.save(updated_vault)

    assert vault_repository.get() == updated_vault
