from datetime import datetime
from uuid import UUID

import pytest

from password_management_context.application.commands import GetPasswordCommand
from password_management_context.application.use_cases import GetPasswordUseCase
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import (
    PasswordAccessDeniedError,
    PasswordNotFoundError,
)
from password_management_context.domain.value_objects import (
    PasswordPermission,
)
from tests.fakes import FakeDomainEventPublisher

from ..fakes import (
    FakeGroupAccessGateway,
    FakePasswordEncryptionGateway,
    FakePasswordEventRepository,
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
)


@pytest.fixture
def use_case(
    password_repository: FakePasswordRepository,
    password_encryption_gateway: FakePasswordEncryptionGateway,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    domain_event_publisher: FakeDomainEventPublisher,
    password_event_repository: FakePasswordEventRepository,
):
    return GetPasswordUseCase(
        password_repository,
        password_encryption_gateway,
        password_permissions_repository,
        group_access_gateway,
        domain_event_publisher,
        password_event_repository,
    )


def test_given_user_with_read_permission_when_getting_password_should_return_decrypted_password(
    use_case: GetPasswordUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository,
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
    password_permissions_repository.grant_access(group_id, password_entity.id, PasswordPermission.READ)
    group_access_gateway.set_group_owner(group_id, user_id)

    # Add creation event
    password_event_repository.append_event(
        event_id=UUID("10e2eb69-5d6b-4500-947a-6636c8755b3f"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 1, 10, 0, 0),
        password_id=password_entity.id,
        actor_user_id=user_id,
        event_data={
            "password_id": str(password_entity.id),
            "password_name": "Gmail",
            "owner_group_id": str(group_id),
            "folder": "default",
        },
    )

    command = GetPasswordCommand(requester_id=user_id, password_id=password_entity.id)
    result = use_case.execute(command)

    assert result.id == password_entity.id
    assert result.name == password_entity.name
    assert result.password == "supersecret"


def test_given_user_without_access_when_getting_password_should_raise_access_denied_error(
    use_case: GetPasswordUseCase,
    password_repository: FakePasswordRepository,
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

    command = GetPasswordCommand(requester_id=user_id, password_id=password_id)
    with pytest.raises(PasswordAccessDeniedError):
        use_case.execute(command)


def test_given_password_not_exists_when_getting_password_should_raise_password_not_found_error(
    use_case: GetPasswordUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
):
    user_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")
    non_existent_password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")

    password_permissions_repository.set_owner(user_id, non_existent_password_id)

    command = GetPasswordCommand(requester_id=user_id, password_id=non_existent_password_id)
    with pytest.raises(PasswordNotFoundError):
        use_case.execute(command)


def test_given_user_is_owner_when_getting_password_should_return_decrypted_password(
    use_case: GetPasswordUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository,
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

    # Add creation event
    password_event_repository.append_event(
        event_id=UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e5"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 1, 10, 0, 0),
        password_id=password_entity.id,
        actor_user_id=user_id,
        event_data={
            "password_id": str(password_entity.id),
            "password_name": "Gmail",
            "owner_group_id": str(group_id),
            "folder": "default",
        },
    )

    command = GetPasswordCommand(requester_id=user_id, password_id=password_entity.id)
    result = use_case.execute(command)

    assert result.id == password_entity.id
    assert result.name == password_entity.name
    assert result.password == "supersecret"


def test_given_user_is_group_member_when_getting_password_should_return_decrypted_password(
    use_case: GetPasswordUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository,
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
    group_access_gateway.add_group_member(group_id, user_id)
    password_permissions_repository.grant_access(group_id, password_entity.id, PasswordPermission.READ)

    # Add creation event
    password_event_repository.append_event(
        event_id=UUID("0d742e0e-bb76-4728-83ef-8d546d7c62e5"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 1, 10, 0, 0),
        password_id=password_entity.id,
        actor_user_id=user_id,
        event_data={
            "password_id": str(password_entity.id),
            "password_name": "Gmail",
            "owner_group_id": str(group_id),
            "folder": "default",
        },
    )

    command = GetPasswordCommand(requester_id=user_id, password_id=password_entity.id)
    result = use_case.execute(command)

    assert result.id == password_entity.id
    assert result.name == password_entity.name
    assert result.password == "supersecret"
    result = use_case.execute(command)

    assert result.id == password_entity.id
    assert result.name == password_entity.name
    assert result.password == "supersecret"


def test_given_password_with_creation_event_when_getting_password_should_return_created_at_date(
    use_case: GetPasswordUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    password_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")
    password_entity = Password(
        id=password_id,
        name="Gmail",
        encrypted_value="encrypted(supersecret)",
        folder="default",
    )
    password_repository.save(password_entity)
    password_permissions_repository.set_owner(group_id, password_entity.id)
    group_access_gateway.set_group_owner(group_id, user_id)

    creation_date = datetime(2025, 1, 15, 10, 30, 0)
    password_event_repository.append_event(
        event_id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        event_type="PasswordCreatedEvent",
        occurred_on=creation_date,
        password_id=password_id,
        actor_user_id=user_id,
        event_data={
            "password_id": str(password_id),
            "password_name": "Gmail",
            "owner_group_id": str(group_id),
            "folder": "default",
        },
    )

    command = GetPasswordCommand(requester_id=user_id, password_id=password_entity.id)
    result = use_case.execute(command)

    assert result.created_at == creation_date


def test_given_password_with_password_update_events_when_getting_password_should_return_last_password_updated_at(
    use_case: GetPasswordUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    password_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")
    password_entity = Password(
        id=password_id,
        name="Gmail",
        encrypted_value="encrypted(newsecret)",
        folder="default",
    )
    password_repository.save(password_entity)
    password_permissions_repository.set_owner(group_id, password_entity.id)
    group_access_gateway.set_group_owner(group_id, user_id)

    # Add creation event
    creation_date = datetime(2025, 1, 15, 10, 0, 0)
    password_event_repository.append_event(
        event_id=UUID("c0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        event_type="PasswordCreatedEvent",
        occurred_on=creation_date,
        password_id=password_id,
        actor_user_id=user_id,
        event_data={
            "password_id": str(password_id),
            "password_name": "Gmail",
            "owner_group_id": str(group_id),
            "folder": "default",
        },
    )

    first_update = datetime(2025, 1, 16, 10, 0, 0)
    password_event_repository.append_event(
        event_id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        event_type="PasswordUpdatedEvent",
        occurred_on=first_update,
        password_id=password_id,
        actor_user_id=user_id,
        event_data={
            "password_id": str(password_id),
            "has_name_changed": False,
            "has_password_changed": True,
            "has_folder_changed": False,
        },
    )

    second_update = datetime(2025, 1, 20, 14, 30, 0)
    password_event_repository.append_event(
        event_id=UUID("a0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        event_type="PasswordUpdatedEvent",
        occurred_on=second_update,
        password_id=password_id,
        actor_user_id=user_id,
        event_data={
            "password_id": str(password_id),
            "has_name_changed": False,
            "has_password_changed": True,
            "has_folder_changed": False,
        },
    )

    command = GetPasswordCommand(requester_id=user_id, password_id=password_entity.id)
    result = use_case.execute(command)

    assert result.last_password_updated_at == second_update


def test_given_password_with_only_name_folder_updates_when_getting_password_should_return_none_for_last_password_updated_at(
    use_case: GetPasswordUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    password_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")
    password_entity = Password(
        id=password_id,
        name="Gmail Updated",
        encrypted_value="encrypted(supersecret)",
        folder="work",
    )
    password_repository.save(password_entity)
    password_permissions_repository.set_owner(group_id, password_entity.id)
    group_access_gateway.set_group_owner(group_id, user_id)

    # Add creation event
    creation_date = datetime(2025, 1, 15, 10, 0, 0)
    password_event_repository.append_event(
        event_id=UUID("f0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        event_type="PasswordCreatedEvent",
        occurred_on=creation_date,
        password_id=password_id,
        actor_user_id=user_id,
        event_data={
            "password_id": str(password_id),
            "password_name": "Gmail",
            "owner_group_id": str(group_id),
            "folder": "default",
        },
    )

    name_update = datetime(2025, 1, 16, 10, 0, 0)
    password_event_repository.append_event(
        event_id=UUID("e0e2cb69-5d6b-4500-947a-6636c8755b3f"),
        event_type="PasswordUpdatedEvent",
        occurred_on=name_update,
        password_id=password_id,
        actor_user_id=user_id,
        event_data={
            "password_id": str(password_id),
            "has_name_changed": True,
            "has_password_changed": False,
            "has_folder_changed": False,
        },
    )

    folder_update = datetime(2025, 1, 20, 14, 30, 0)
    password_event_repository.append_event(
        event_id=UUID("a0e2cb09-5d6b-4500-947a-6636c8755b3f"),
        event_type="PasswordUpdatedEvent",
        occurred_on=folder_update,
        password_id=password_id,
        actor_user_id=user_id,
        event_data={
            "password_id": str(password_id),
            "has_name_changed": False,
            "has_password_changed": False,
            "has_folder_changed": True,
        },
    )

    command = GetPasswordCommand(requester_id=user_id, password_id=password_entity.id)
    result = use_case.execute(command)

    # When there's no password change event, last_password_updated_at equals created_at
    assert result.last_password_updated_at == creation_date
    assert result.created_at == creation_date


def test_given_password_without_update_events_when_getting_password_should_return_created_at_for_last_password_updated_at(
    use_case: GetPasswordUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    password_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")
    password_entity = Password(
        id=password_id,
        name="Gmail",
        encrypted_value="encrypted(supersecret)",
        folder="default",
    )
    password_repository.save(password_entity)
    password_permissions_repository.set_owner(group_id, password_entity.id)
    group_access_gateway.set_group_owner(group_id, user_id)

    creation_date = datetime(2025, 1, 15, 10, 30, 0)
    password_event_repository.append_event(
        event_id=UUID("e0e2cb69-5d6b-4500-947a-6636c8755b3f"),
        event_type="PasswordCreatedEvent",
        occurred_on=creation_date,
        password_id=password_id,
        actor_user_id=user_id,
        event_data={
            "password_id": str(password_id),
            "password_name": "Gmail",
            "owner_group_id": str(group_id),
            "folder": "default",
        },
    )

    command = GetPasswordCommand(requester_id=user_id, password_id=password_entity.id)
    result = use_case.execute(command)

    assert result.created_at == creation_date
    assert result.last_password_updated_at == creation_date
