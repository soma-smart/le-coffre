import pytest

from src.vault_management_context.adapters.secondary.gateways.crypto_shamir_gateway import (
    CryptoShamirGateway,
)
from src.vault_management_context.business_logic.use_cases.create_vault_use_case import (
    CreateVaultUseCase,
)
from src.vault_management_context.business_logic.models.value_objects.vault import (
    Vault,
)
from src.vault_management_context.adapters.secondary.gateways.fake_vault_repository import (
    FakeVaultRepository,
)


@pytest.fixture()
def vault_repo():
    return FakeVaultRepository()


@pytest.fixture()
def shamir_gateway():
    return CryptoShamirGateway()


@pytest.fixture()
def use_case(vault_repo, shamir_gateway):
    return CreateVaultUseCase(vault_repo, shamir_gateway)


def test_should_create_vault(use_case, vault_repo):
    vault = use_case.execute(5, 3)

    assert vault_repo.get() == vault


def test_should_failt_when_vault_is_already_created(use_case, vault_repo):
    vault_repo.save(Vault(5, 3, []))

    with pytest.raises(ValueError) as exc_info:
        use_case.execute(5, 3)

    assert str(exc_info.value) == "Already setup"


def test_should_fail_when_nb_shares_is_less_than_2(use_case):
    with pytest.raises(ValueError) as exc_info:
        use_case.execute(1, 2)

    assert str(exc_info.value) == "Number of shares must be at least 2"


def test_should_fail_when_threshold_is_less_than_2(use_case):
    with pytest.raises(ValueError) as exc_info:
        use_case.execute(3, 1)

    assert str(exc_info.value) == "Threshold must be at least 2"


def test_should_fail_when_threshold_is_greater_than_nb_shares(use_case):
    with pytest.raises(ValueError) as exc_info:
        use_case.execute(3, 4)

    assert str(exc_info.value) == "Threshold cannot be greater than number of shares"
