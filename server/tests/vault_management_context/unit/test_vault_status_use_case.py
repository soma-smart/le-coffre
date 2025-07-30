import pytest

from src.vault_management_context.application.gateways import (
    VaultRepository,
)
from src.vault_management_context.application.use_cases import GetVaultStatusUseCase
from src.vault_management_context.domain.models import Vault


@pytest.fixture()
def use_case(vault_repository):
    return GetVaultStatusUseCase(vault_repository)


def test_should_fail_when_no_status_exists(use_case: GetVaultStatusUseCase):
    status_existing = use_case.execute()

    assert status_existing is False


def test_should_succeed_when_status_exists(
    vault_repository: VaultRepository, use_case: GetVaultStatusUseCase
):
    vault_repository.save(Vault(3, 2, []))
    status_existing = use_case.execute()

    assert status_existing is True
