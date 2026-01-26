import pytest
from uuid import UUID

from password_management_context.application.use_cases import DeletePasswordUseCase
from password_management_context.application.gateways import (
    PasswordPermissionsRepository,
)
from password_management_context.adapters.secondary import (
    InMemoryPasswordRepository,
)
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    UserNotOwnerOfGroupError,
)
from password_management_context.domain.entities import Password
from password_management_context.domain.events import PasswordDeletedEvent
from tests.shared_kernel.fakes import FakeEventPublisher


@pytest.fixture
def use_case(
    password_repository,
    password_permissions_repository,
    group_access_gateway,
    event_publisher,
):
    return DeletePasswordUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
    )


def test_given_owner_when_deleting_should_success(
    use_case: DeletePasswordUseCase,
    password_repository: InMemoryPasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway,
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
    group_access_gateway,
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

    with pytest.raises(UserNotOwnerOfGroupError):
        use_case.execute(requester_id, resource.id)


def test_should_publish_password_deleted_event_when_password_is_deleted(
    use_case: DeletePasswordUseCase,
    password_repository: InMemoryPasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway,
    event_publisher: FakeEventPublisher,
):
    requester_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    owner_group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e8")
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    password_name = "MyPassword"

    resource = Password(
        id=password_id,
        name=password_name,
        encrypted_value="encrypted(MyPassword)",
        folder="folder",
    )
    password_repository.save(resource)
    password_permissions_repository.set_owner(owner_group_id, resource.id)
    group_access_gateway.set_group_owner(owner_group_id, requester_id)

    use_case.execute(requester_id, resource.id)

    # Assert event was published
    assert len(event_publisher.published_events) == 1
    published_event = event_publisher.published_events[0]
    assert isinstance(published_event, PasswordDeletedEvent)
    assert published_event.password_id == password_id
    assert published_event.password_name == password_name
    assert published_event.deleted_by_user_id == requester_id
    assert published_event.owner_group_id == owner_group_id
