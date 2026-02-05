import pytest
from uuid import UUID

from password_management_context.application.commands import (
    DeletePasswordsForDeletedUserCommand,
)
from password_management_context.application.use_cases import (
    DeletePasswordsForDeletedUserUseCase,
)
from password_management_context.domain.value_objects import PasswordPermission
from ..fakes import (
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
)
from tests.fakes import FakeDomainEventPublisher
from password_management_context.domain.entities import Password
from password_management_context.domain.events import PasswordDeletedEvent
from password_management_context.domain.exceptions import PasswordNotFoundError


@pytest.fixture
def use_case(
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    domain_event_publisher: FakeDomainEventPublisher,
):
    return DeletePasswordsForDeletedUserUseCase(
        password_repository,
        password_permissions_repository,
        domain_event_publisher,
    )


def test_given_user_with_passwords_when_user_deleted_should_delete_all_passwords(
    use_case: DeletePasswordsForDeletedUserUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
):
    personal_group_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_user_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    password1_id = UUID("323e4567-e89b-12d3-a456-426614174002")
    password2_id = UUID("423e4567-e89b-12d3-a456-426614174003")

    password1 = Password(
        id=password1_id,
        name="Password 1",
        encrypted_value="encrypted1",
        folder="folder",
    )
    password2 = Password(
        id=password2_id,
        name="Password 2",
        encrypted_value="encrypted2",
        folder="folder",
    )

    password_repository.save(password1)
    password_repository.save(password2)
    password_repository.set_owner_for_password(password1_id, personal_group_id)
    password_repository.set_owner_for_password(password2_id, personal_group_id)
    password_permissions_repository.set_owner(personal_group_id, password1_id)
    password_permissions_repository.set_owner(personal_group_id, password2_id)

    command = DeletePasswordsForDeletedUserCommand(
        personal_group_id=personal_group_id,
        deleted_by_user_id=admin_user_id,
    )

    use_case.execute(command)

    with pytest.raises(PasswordNotFoundError):
        password_repository.get_by_id(password1_id)
    with pytest.raises(PasswordNotFoundError):
        password_repository.get_by_id(password2_id)


def test_given_user_with_passwords_when_user_deleted_should_remove_all_permissions(
    use_case: DeletePasswordsForDeletedUserUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
):
    personal_group_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_user_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    password_id = UUID("323e4567-e89b-12d3-a456-426614174002")
    other_user_id = UUID("523e4567-e89b-12d3-a456-426614174005")

    password = Password(
        id=password_id,
        name="Password 1",
        encrypted_value="encrypted1",
        folder="folder",
    )

    password_repository.save(password)
    password_repository.set_owner_for_password(password_id, personal_group_id)
    password_permissions_repository.set_owner(personal_group_id, password_id)
    password_permissions_repository.grant_access(
        other_user_id, password_id, PasswordPermission.READ
    )

    command = DeletePasswordsForDeletedUserCommand(
        personal_group_id=personal_group_id,
        deleted_by_user_id=admin_user_id,
    )

    use_case.execute(command)

    all_perms = password_permissions_repository.list_all_permissions_for(password_id)
    assert len(all_perms) == 0


def test_given_user_with_passwords_when_user_deleted_should_publish_events(
    use_case: DeletePasswordsForDeletedUserUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    domain_event_publisher: FakeDomainEventPublisher,
):
    personal_group_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_user_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    password1_id = UUID("323e4567-e89b-12d3-a456-426614174002")
    password2_id = UUID("423e4567-e89b-12d3-a456-426614174003")

    password1 = Password(
        id=password1_id,
        name="Password 1",
        encrypted_value="encrypted1",
        folder="folder",
    )
    password2 = Password(
        id=password2_id,
        name="Password 2",
        encrypted_value="encrypted2",
        folder="folder",
    )

    password_repository.save(password1)
    password_repository.save(password2)
    password_repository.set_owner_for_password(password1_id, personal_group_id)
    password_repository.set_owner_for_password(password2_id, personal_group_id)
    password_permissions_repository.set_owner(personal_group_id, password1_id)
    password_permissions_repository.set_owner(personal_group_id, password2_id)

    command = DeletePasswordsForDeletedUserCommand(
        personal_group_id=personal_group_id,
        deleted_by_user_id=admin_user_id,
    )

    use_case.execute(command)

    assert len(domain_event_publisher.published_events) == 2
    for event in domain_event_publisher.published_events:
        assert isinstance(event, PasswordDeletedEvent)
        assert event.owner_group_id == personal_group_id
        assert event.deleted_by_user_id == admin_user_id


def test_given_user_without_passwords_when_user_deleted_should_do_nothing(
    use_case: DeletePasswordsForDeletedUserUseCase,
    domain_event_publisher: FakeDomainEventPublisher,
):
    personal_group_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_user_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    command = DeletePasswordsForDeletedUserCommand(
        personal_group_id=personal_group_id,
        deleted_by_user_id=admin_user_id,
    )

    use_case.execute(command)

    assert len(domain_event_publisher.published_events) == 0
