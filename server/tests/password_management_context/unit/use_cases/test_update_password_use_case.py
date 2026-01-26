import pytest
from uuid import UUID

from password_management_context.adapters.secondary import (
    InMemoryPasswordRepository,
)
from password_management_context.application.use_cases import UpdatePasswordUseCase
from password_management_context.domain.entities import Password
from password_management_context.application.commands import UpdatePasswordCommand
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    NotPasswordOwnerError,
)
from password_management_context.application.gateways.password_permissions_repository import (
    PasswordPermissionsRepository,
)
from password_management_context.domain.events import PasswordUpdatedEvent
from tests.shared_kernel.fakes import FakeEventPublisher


@pytest.fixture
def use_case(
    password_repository,
    encryption_service,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway,
    event_publisher,
):
    return UpdatePasswordUseCase(
        password_repository,
        encryption_service,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
    )


def test_should_update_password(
    use_case: UpdatePasswordUseCase,
    password_repository: InMemoryPasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e6")
    original_password = Password(
        id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"),
        name="original",
        encrypted_value="encrypted(original)",
        folder="folder",
    )
    password_repository.save(original_password)
    # Set group as owner and user as owner of group
    password_permissions_repository.set_owner(group_id, original_password.id)
    group_access_gateway.set_group_owner(group_id, requester_id)

    updated_password = UpdatePasswordCommand(
        requester_id=requester_id,
        id=original_password.id,
        name="updated",
        password="updated",
        folder="folder",
    )

    use_case.execute(new_password=updated_password)

    assert password_repository.get_by_id(original_password.id).name == "updated"
    assert (
        password_repository.get_by_id(original_password.id).encrypted_value
        == "encrypted(updated)"
    )


# For security purpose, PasswordNotFound and AccessDenied are indistinguishable
def test_when_requesting_a_non_existing_password_should_raise_password_not_found(
    use_case: UpdatePasswordUseCase,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e5")
    non_existent_password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    password_data = UpdatePasswordCommand(
        requester_id=requester_id,
        id=non_existent_password_id,
        name="original",
        password="encrypted(original)",
        folder="folder",
    )

    with pytest.raises(PasswordNotFoundError):
        use_case.execute(password_data)


def test_update_password_without_access(
    use_case: UpdatePasswordUseCase,
    password_repository: InMemoryPasswordRepository,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e5")
    original_password = Password(
        id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"),
        name="original",
        encrypted_value="encrypted(original)",
        folder="folder",
    )
    password_repository.save(original_password)

    updated_password = UpdatePasswordCommand(
        requester_id=requester_id,
        id=original_password.id,
        name="updated",
        password="updated",
        folder="folder",
    )

    with pytest.raises(NotPasswordOwnerError):
        use_case.execute(new_password=updated_password)


def test_when_updating_without_any_element_changed_should_not_change_anything(
    use_case: UpdatePasswordUseCase,
    password_repository: InMemoryPasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e6")
    original_password = Password(
        id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"),
        name="original",
        encrypted_value="encrypted(original)",
        folder="folder",
    )
    password_repository.save(original_password)
    # Set group as owner and user as owner of group
    password_permissions_repository.set_owner(group_id, original_password.id)
    group_access_gateway.set_group_owner(group_id, requester_id)

    updated_password = UpdatePasswordCommand(
        requester_id=requester_id,
        id=original_password.id,
    )

    use_case.execute(new_password=updated_password)

    stored_password = password_repository.get_by_id(original_password.id)

    assert stored_password.name == "original"
    assert stored_password.encrypted_value == "encrypted(original)"
    assert stored_password.folder == "folder"


def test_should_publish_password_updated_event_when_password_is_updated(
    use_case: UpdatePasswordUseCase,
    password_repository: InMemoryPasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway,
    event_publisher: FakeEventPublisher,
):
    requester_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    owner_group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e8")
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    new_name = "UpdatedPassword"
    new_folder = "new-folder"

    password = Password(
        id=password_id,
        name="OldName",
        encrypted_value="encrypted(OldPassword)",
        folder="old-folder",
    )
    password_repository.save(password)
    password_permissions_repository.set_owner(owner_group_id, password.id)
    group_access_gateway.set_group_owner(owner_group_id, requester_id)

    command = UpdatePasswordCommand(
        id=password.id,
        requester_id=requester_id,
        name=new_name,
        password="NewPassword",
        folder=new_folder,
    )

    use_case.execute(command)

    # Assert event was published
    assert len(event_publisher.published_events) == 1
    published_event = event_publisher.published_events[0]
    assert isinstance(published_event, PasswordUpdatedEvent)
    assert published_event.password_id == password_id
    assert published_event.password_name == new_name
    assert published_event.updated_by_user_id == requester_id
    assert published_event.owner_group_id == owner_group_id
    assert published_event.folder == new_folder
