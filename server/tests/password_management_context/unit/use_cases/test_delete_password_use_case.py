import pytest
from uuid import UUID

from password_management_context.application.use_cases import DeletePasswordUseCase
from password_management_context.application.gateways import (
    PasswordPermissionsRepository,
)
from password_management_context.adapters.secondary.gateways import (
    InMemoryPasswordRepository,
)
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    NotPasswordOwnerError,
)
from password_management_context.domain.entities import Password


@pytest.fixture
def use_case(password_repository, password_permissions_repository):
    return DeletePasswordUseCase(password_repository, password_permissions_repository)


def test_given_owner_when_deleting_should_success(
    use_case: DeletePasswordUseCase,
    password_repository: InMemoryPasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
):
    requester_user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
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
    password_permissions_repository.set_owner(requester_user_id, password.id)

    use_case.execute(requester_user_id, uuid)

    with pytest.raises(PasswordNotFoundError):
        password_repository.get_by_id(uuid)


def test_should_raise_error_when_password_does_not_exist(
    use_case: DeletePasswordUseCase,
):
    requester_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    fake_resource_uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    with pytest.raises(PasswordNotFoundError):
        use_case.execute(requester_id, fake_resource_uuid)


def test_given_non_owner_when_deleting_should_fail(
    use_case: DeletePasswordUseCase,
    password_repository: InMemoryPasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
):
    requester_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    owner_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e7")
    resource = Password(
        id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"),
        name="MyPassword",
        encrypted_value="encrypted(MyPassword)",
        folder="folder",
    )
    password_repository.save(resource)
    password_permissions_repository.set_owner(owner_id, resource.id)

    with pytest.raises(NotPasswordOwnerError):
        use_case.execute(requester_id, resource.id)
