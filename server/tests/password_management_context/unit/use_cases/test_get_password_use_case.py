import pytest
from uuid import UUID

from password_management_context.application.use_cases import GetPasswordUseCase
from password_management_context.application.gateways import (
    PasswordPermissionsRepository,
)
from password_management_context.adapters.secondary.gateways import (
    InMemoryPasswordRepository,
)
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    PasswordAccessDeniedError,
)
from password_management_context.domain.entities import Password


@pytest.fixture
def use_case(password_repository, encryption_service, password_permissions_repository):
    return GetPasswordUseCase(
        password_repository, encryption_service, password_permissions_repository
    )


def test_should_return_password_when_user_has_access(
    use_case: GetPasswordUseCase,
    password_repository,
    password_permissions_repository: PasswordPermissionsRepository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    password_entity = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(supersecret)",
        folder="default",
    )
    password_repository.save(password_entity)
    password_permissions_repository.set_owner(user_id, password_entity.id)

    result = use_case.execute(user_id, password_entity.id)

    assert result.id == password_entity.id
    assert result.name == password_entity.name
    assert result.password == "supersecret"


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

    with pytest.raises(PasswordAccessDeniedError):
        use_case.execute(user_id, password_id)


def test_should_raise_exception_when_password_not_found(
    use_case: GetPasswordUseCase,
    password_permissions_repository: PasswordPermissionsRepository,
):
    user_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")
    non_existent_password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")

    password_permissions_repository.set_owner(user_id, non_existent_password_id)

    with pytest.raises(PasswordNotFoundError):
        use_case.execute(user_id, non_existent_password_id)


def test_should_return_password_when_owner(
    use_case: GetPasswordUseCase,
    password_repository,
    password_permissions_repository: PasswordPermissionsRepository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    password_entity = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(supersecret)",
        folder="default",
    )
    password_repository.save(password_entity)
    password_permissions_repository.set_owner(user_id, password_entity.id)

    result = use_case.execute(user_id, password_entity.id)

    assert result.id == password_entity.id
    assert result.name == password_entity.name
    assert result.password == "supersecret"
