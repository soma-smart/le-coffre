import pytest
from uuid import UUID

from password_management_context.application.commands import DeletePasswordCommand
from password_management_context.application.use_cases import DeletePasswordUseCase
from ..fakes import (
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
    FakeGroupAccessGateway,
)
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    UserNotOwnerOfGroupError,
)
from password_management_context.domain.entities import Password


@pytest.fixture
def use_case(
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
):
    return DeletePasswordUseCase(
        password_repository, password_permissions_repository, group_access_gateway
    )


def test_given_owner_when_deleting_should_success(
    use_case: DeletePasswordUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
):
    requester_user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")  # Group owned by user
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
    # Set group as owner of password
    password_permissions_repository.set_owner(group_id, password.id)
    # Set user as owner of the group
    group_access_gateway.set_group_owner(group_id, requester_user_id)

    command = DeletePasswordCommand(requester_id=requester_user_id, password_id=uuid)
    use_case.execute(command)

    with pytest.raises(PasswordNotFoundError):
        password_repository.get_by_id(uuid)


def test_given_password_not_exists_when_deleting_password_should_raise_password_not_found_error(
    use_case: DeletePasswordUseCase,
):
    requester_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    fake_resource_uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")

    command = DeletePasswordCommand(
        requester_id=requester_id, password_id=fake_resource_uuid
    )
    with pytest.raises(PasswordNotFoundError):
        use_case.execute(command)


def test_given_non_owner_when_deleting_should_fail(
    use_case: DeletePasswordUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
):
    requester_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    owner_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e7")
    owner_group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e8")
    resource = Password(
        id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"),
        name="MyPassword",
        encrypted_value="encrypted(MyPassword)",
        folder="folder",
    )
    password_repository.save(resource)
    # Set group as owner of password
    password_permissions_repository.set_owner(owner_group_id, resource.id)
    # Set owner_id (not requester) as owner of the group
    group_access_gateway.set_group_owner(owner_group_id, owner_id)

    command = DeletePasswordCommand(requester_id=requester_id, password_id=resource.id)
    with pytest.raises(UserNotOwnerOfGroupError):
        use_case.execute(command)
