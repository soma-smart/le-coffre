import pytest

from vault_management_context.domain.entities import (
    Vault,
)
from vault_management_context.domain.exceptions import (
    VaultAlreadyExistsError,
    InvalidShareCountError,
    InvalidThresholdError,
    ThresholdExceedsShareCountError,
)
from vault_management_context.application.use_cases import (
    CreateVaultUseCase,
)


@pytest.fixture()
def use_case(vault_repository, shamir_gateway):
    return CreateVaultUseCase(vault_repository, shamir_gateway)


def test_should_create_shares(use_case, vault_repository):
    shares = use_case.execute(5, 3)

    assert vault_repository.get().shares == shares


def test_should_fail_when_vault_is_already_created(use_case, vault_repository):
    vault_repository.save(Vault(5, 3, []))

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
