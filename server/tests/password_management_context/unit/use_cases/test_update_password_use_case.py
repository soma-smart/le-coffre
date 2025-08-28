import pytest
from uuid import UUID

from password_management_context.adapters.secondary.gateways import (
    InMemoryPasswordRepository,
)
from password_management_context.application.use_cases import UpdatePasswordUseCase
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import PasswordNotFoundError
from password_management_context.application.commands import CreatePasswordCommand


@pytest.fixture
def use_case(password_repository, encryption_service):
    return UpdatePasswordUseCase(password_repository, encryption_service)


def test_should_update_password(
    use_case: UpdatePasswordUseCase, password_repository: InMemoryPasswordRepository
):
    # Arrange
    original_password = Password(
        id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"),
        name="original",
        encrypted_value="encrypted(original)",
        folder="folder",
    )
    password_repository.save(original_password)
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    updated_password = CreatePasswordCommand(
        user_id=user_id,
        id=original_password.id,
        name="updated",
        decrypted_password="updated",
        folder="folder",
    )

    # Act
    use_case.execute(new_password=updated_password)

    # Assert
    assert password_repository.get_by_id(original_password.id).name == "updated"
    assert (
        password_repository.get_by_id(original_password.id).encrypted_value
        == "encrypted(updated)"
    )


def test_should_raise_exception_when_password_not_found(
    use_case: UpdatePasswordUseCase,
):
    non_existent_password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    password_data = CreatePasswordCommand(
        user_id=user_id,
        id=non_existent_password_id,
        name="original",
        decrypted_password="encrypted(original)",
        folder="folder",
    )

    with pytest.raises(PasswordNotFoundError):
        use_case.execute(password_data)
