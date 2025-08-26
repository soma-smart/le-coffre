import pytest
from uuid import UUID

from password_management_context.application.use_cases import DeletePasswordUseCase
from password_management_context.adapters.secondary.gateways import (
    InMemoryPasswordRepository
)
from password_management_context.domain.exceptions import PasswordNotFoundError
from password_management_context.domain.entities import Password


@pytest.fixture
def use_case(password_repository):
    return DeletePasswordUseCase(password_repository)


def test_sould_delete_password_when_it_exists(
    use_case: DeletePasswordUseCase, password_repository: InMemoryPasswordRepository
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    name = "name"
    folder = "folder"
    encrypted_password = "encrypted(secret123)"

    password = Password(
        id=uuid,
        name=name,
        encrypted_value=encrypted_password,
        folder=folder,
    )
    password_repository.save(password)

    use_case.execute(uuid)

    with pytest.raises(PasswordNotFoundError):
        password_repository.get_by_id(uuid)


def test_sould_raise_error_when_password_does_not_exist(
    use_case: DeletePasswordUseCase,
):
    with pytest.raises(PasswordNotFoundError):
        use_case.execute(UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"))
