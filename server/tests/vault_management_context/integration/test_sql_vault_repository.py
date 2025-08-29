import pytest

from vault_management_context.domain.entities.vault import Vault


def test_when_no_vault_should_not_get_any(vault_repository):
    result = vault_repository.get()
    assert result == None


def test_when_vault_in_repo_should_get_it(vault_repository):
    vault = Vault(2, 2, "encrypted_key")

    vault_repository.save(vault)
    assert vault_repository.get() == vault


def test_when_updating_vault_should_update_it(vault_repository):
    vault = Vault(2, 2, "encrypted_key")
    vault_repository.save(vault)

    updated_vault = Vault(2, 2, "new_encrypted_key")
    vault_repository.save(updated_vault)

    assert vault_repository.get() == updated_vault
