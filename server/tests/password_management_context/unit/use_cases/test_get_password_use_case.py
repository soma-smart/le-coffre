import pytest
from uuid import UUID

from password_management_context.application.use_cases import GetPasswordUseCase
from password_management_context.application.gateways import (
    PasswordPermissionsRepository,
)
from password_management_context.adapters.secondary import (
    InMemoryPasswordRepository,
)
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    PasswordAccessDeniedError,
)
from password_management_context.domain.entities import Password
from password_management_context.domain.value_objects import (
    PasswordPermission,
)


@pytest.fixture
def use_case(
    password_repository,
    encryption_service,
    password_permissions_repository,
    group_access_gateway,
):
    return GetPasswordUseCase(
        password_repository,
        encryption_service,
        password_permissions_repository,
        group_access_gateway,
    )


def test_should_return_password_when_user_has_access(
    use_case: GetPasswordUseCase,
    password_repository: InMemoryPasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    password_entity = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(supersecret)",
        folder="default",
    )
    password_repository.save(password_entity)
    # Grant READ permission to group and set user as owner of group
    password_permissions_repository.grant_access(
        group_id, password_entity.id, PasswordPermission.READ
    )
    group_access_gateway.set_group_owner(group_id, user_id)

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
    group_access_gateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    password_entity = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(supersecret)",
        folder="default",
    )
    password_repository.save(password_entity)
    # Set group as owner and user as owner of group
    password_permissions_repository.set_owner(group_id, password_entity.id)
    group_access_gateway.set_group_owner(group_id, user_id)

    result = use_case.execute(user_id, password_entity.id)

    assert result.id == password_entity.id
    assert result.name == password_entity.name
    assert result.password == "supersecret"
