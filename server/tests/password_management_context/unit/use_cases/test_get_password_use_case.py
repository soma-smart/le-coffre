import pytest
from uuid import UUID

from password_management_context.application.use_cases import GetPasswordUseCase
from password_management_context.adapters.secondary.gateways import (
    InMemoryPasswordRepository,
)
from password_management_context.domain.exceptions import PasswordNotFoundError
from password_management_context.domain.entities import Password
from shared_kernel.access_control import AccessDeniedError

from ..mocks import FakeAccessChecker


@pytest.fixture
def use_case(password_repository, encryption_service, access_checker):
    return GetPasswordUseCase(password_repository, encryption_service, access_checker)


def test_should_return_decrypted_password_when_user_has_access(
    use_case: GetPasswordUseCase,
    password_repository: InMemoryPasswordRepository,
    access_checker: FakeAccessChecker,
):
    user_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    name = "name"
    folder = "folder"
    encrypted_password = "encrypted(secret123)"
    expected_decrypted = "secret123"

    password = Password(
        id=password_id,
        name=name,
        encrypted_value=encrypted_password,
        folder=folder,
    )
    password_repository.save(password)
    access_checker.grant_access(user_id, password_id)

    result = use_case.execute(user_id, password_id)

    assert result.id == password_id
    assert result.name == name
    assert result.folder == folder
    assert result.decrypted_password == expected_decrypted


def test_should_raise_access_denied_when_user_has_no_access(
    use_case: GetPasswordUseCase,
    password_repository: InMemoryPasswordRepository,
):
    user_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")

    password = Password(
        id=password_id,
        name="name",
        encrypted_value="encrypted(secret123)",
        folder="folder",
    )
    password_repository.save(password)

    with pytest.raises(AccessDeniedError):
        use_case.execute(user_id, password_id)


def test_should_raise_exception_when_password_not_found(
    use_case: GetPasswordUseCase, access_checker: FakeAccessChecker
):
    user_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")
    non_existent_password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")

    access_checker.grant_access(user_id, non_existent_password_id)

    with pytest.raises(PasswordNotFoundError):
        use_case.execute(user_id, non_existent_password_id)
