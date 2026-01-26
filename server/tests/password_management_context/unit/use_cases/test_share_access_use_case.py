from uuid import UUID, uuid4
import pytest
from password_management_context.application.use_cases import (
    ShareAccessUseCase,
)
from password_management_context.application.commands import ShareResourceCommand
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
)
from password_management_context.domain.value_objects import PasswordPermission
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    UserNotOwnerOfGroupError,
)
from password_management_context.domain.events import PasswordSharedEvent
from tests.shared_kernel.fakes import FakeEventPublisher


@pytest.fixture()
def use_case(
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway,
    event_publisher,
):
    return ShareAccessUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        event_publisher,
    )


@pytest.fixture()
def password():
    return Password(uuid4(), "toto", "encrypted_value", "default")


def test_given_owner_when_sharing_should_grant_read_access(
    use_case: ShareAccessUseCase,
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    password,
    group_access_gateway,
):
    # Arrange: Given an owner of a resource
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    owner_group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    target_group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password_repository.save(password)
    # Set owner group and user as owner of it
    password_permissions_repository.set_owner(owner_group_id, password.id)
    group_access_gateway.set_group_owner(owner_group_id, owner_id)
    # Register target group
    group_access_gateway.set_group_owner(
        target_group_id, UUID("9d742e0e-bb76-4728-83ef-8d546d7c62e7")
    )

    # Act: When owner shares the resource with a group
    use_case.execute(ShareResourceCommand(owner_id, target_group_id, password.id))

    # Assert: Then the target group should have READ access only
    assert password_permissions_repository.has_access(
        target_group_id, password.id, PasswordPermission.READ
    )


def test_given_non_owner_with_permissions_when_sharing_should_fail(
    use_case: ShareAccessUseCase,
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    password,
    group_access_gateway,
):
    # Arrange: Given a user with READ permission but not owner
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    owner_group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    non_owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    non_owner_group_id = UUID("9d742e0e-bb76-4728-83ef-8d546d7c62e7")
    third_group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e8")

    password_repository.save(password)
    # Set owner group
    password_permissions_repository.set_owner(owner_group_id, password.id)
    group_access_gateway.set_group_owner(owner_group_id, owner_id)
    # Grant READ to non-owner group
    password_permissions_repository.grant_access(
        non_owner_group_id, password.id, PasswordPermission.READ
    )
    group_access_gateway.set_group_owner(non_owner_group_id, non_owner_id)
    # Register third group
    group_access_gateway.set_group_owner(
        third_group_id, UUID("ad742e0e-bb76-4728-83ef-8d546d7c62e8")
    )

    # Act & Assert: When non-owner tries to share, then should fail
    with pytest.raises(UserNotOwnerOfGroupError):
        use_case.execute(
            ShareResourceCommand(non_owner_id, third_group_id, password.id)
        )

    # Assert: Third group should not have access
    assert not password_permissions_repository.has_access(
        third_group_id, password.id, PasswordPermission.READ
    )


def test_given_owner_when_sharing_already_shared_resource_should_succeed(
    use_case: ShareAccessUseCase,
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    password,
    group_access_gateway,
):
    # Arrange
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    owner_group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    target_group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password_repository.save(password)
    # Set owner group
    password_permissions_repository.set_owner(owner_group_id, password.id)
    group_access_gateway.set_group_owner(owner_group_id, owner_id)
    # Already grant access to target group
    password_permissions_repository.grant_access(
        target_group_id, password.id, PasswordPermission.READ
    )
    group_access_gateway.set_group_owner(
        target_group_id, UUID("9d742e0e-bb76-4728-83ef-8d546d7c62e7")
    )

    # Act: Share again
    use_case.execute(ShareResourceCommand(owner_id, target_group_id, password.id))

    # Assert: Still has access
    assert password_permissions_repository.has_access(
        target_group_id, password.id, PasswordPermission.READ
    )


def test_given_non_existing_password_when_sharing_should_fail(
    use_case: ShareAccessUseCase,
):
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    with pytest.raises(PasswordNotFoundError):
        use_case.execute(ShareResourceCommand(owner_id, user_id, password_id))


def test_should_publish_password_shared_event_when_password_is_shared(
    use_case: ShareAccessUseCase,
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway,
    event_publisher: FakeEventPublisher,
):
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    owner_group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    target_group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e8")
    password_name = "SharedPassword"

    password = Password(
        id=password_id,
        name=password_name,
        encrypted_value="encrypted(password)",
        folder="folder",
    )
    password_repository.save(password)
    password_permissions_repository.set_owner(owner_group_id, password.id)
    group_access_gateway.set_group_owner(owner_group_id, owner_id)
    # Ensure target group exists
    group_access_gateway.set_group_owner(
        target_group_id, UUID("00000000-0000-0000-0000-000000000000")
    )

    command = ShareResourceCommand(owner_id, target_group_id, password_id)
    use_case.execute(command)

    # Assert event was published
    assert len(event_publisher.published_events) == 1
    published_event = event_publisher.published_events[0]
    assert isinstance(published_event, PasswordSharedEvent)
    assert published_event.password_id == password_id
    assert published_event.password_name == password_name
    assert published_event.shared_with_group_id == target_group_id
    assert published_event.shared_by_user_id == owner_id
    assert published_event.owner_group_id == owner_group_id
    assert published_event.can_write == False
