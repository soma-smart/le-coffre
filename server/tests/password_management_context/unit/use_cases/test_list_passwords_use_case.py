import pytest
from uuid import UUID
from datetime import datetime

from password_management_context.application.commands import ListPasswordsCommand
from password_management_context.application.use_cases import ListPasswordsUseCase

from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import FolderNotFoundError
from ..fakes import (
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
    FakeGroupAccessGateway,
    FakePasswordEventRepository,
)
from password_management_context.domain.value_objects import PasswordPermission
from shared_kernel.domain.entities import AuthenticatedUser


@pytest.fixture
def use_case(
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
):
    return ListPasswordsUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        password_event_repository,
    )


def test_given_no_passwords_when_listing_default_folder_should_return_empty_list(
    use_case: ListPasswordsUseCase,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")

    command = ListPasswordsCommand(
        requester=AuthenticatedUser(user_id=requester_id, roles=[])
    )
    result = use_case.execute(command)

    assert result == []


def test_given_passwords_exist_when_listing_all_folders_should_return_all_accessible_passwords(
    use_case: ListPasswordsUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group1_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group2_id = UUID("3d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password1 = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(gmail_secret)",
        folder="default",
    )
    password2 = Password(
        id=UUID("55050a52-7dc7-47dd-9cc9-33b232f27018"),
        name="Slack",
        encrypted_value="encrypted(slack_secret)",
        folder="Personal",
    )

    password_repository.save(password1)
    password_permissions_repository.set_owner(group1_id, password1.id)
    group_access_gateway.set_group_owner(group1_id, requester_id)
    password_repository.save(password2)
    password_permissions_repository.set_owner(group2_id, password2.id)
    password_permissions_repository.grant_access(
        group2_id, password2.id, PasswordPermission.READ
    )
    group_access_gateway.set_group_owner(group2_id, requester_id)

    # Add creation events for both passwords
    password_event_repository.append_event(
        event_id=UUID("10e2eb69-5d6b-4500-947a-6636c8755b3f"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 1, 10, 0, 0),
        password_id=password1.id,
        actor_user_id=requester_id,
        event_data={
            "password_id": str(password1.id),
            "password_name": "Gmail",
            "owner_group_id": str(group1_id),
            "folder": "default",
        },
    )
    password_event_repository.append_event(
        event_id=UUID("9fd8c527-7dc7-47dd-9cc9-33b232f27018"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 2, 10, 0, 0),
        password_id=password2.id,
        actor_user_id=requester_id,
        event_data={
            "password_id": str(password2.id),
            "password_name": "Slack",
            "owner_group_id": str(group2_id),
            "folder": "Personal",
        },
    )

    command = ListPasswordsCommand(
        requester=AuthenticatedUser(user_id=requester_id, roles=[])
    )
    result = use_case.execute(command)

    assert len(result) == 2

    for i in result:
        assert any(
            p.id == i.id and p.name == i.name and p.folder == i.folder
            for p in [password1, password2]
        )

    # Verify group_id is set correctly
    password1_result = next(r for r in result if r.id == password1.id)
    assert password1_result.group_id == group1_id

    password2_result = next(r for r in result if r.id == password2.id)
    assert password2_result.group_id == group2_id


def test_given_specific_folder_when_listing_passwords_should_return_only_folder_passwords(
    use_case: ListPasswordsUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group1_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group2_id = UUID("3d742e0e-bb76-4728-83ef-8d546d7c62e6")
    folder_name = "Personal"

    password1 = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(gmail_secret)",
        folder=folder_name,
    )
    password2 = Password(
        id=UUID("d5685277-bb51-4223-9825-a72f6a74c6e5"),
        name="Slack",
        encrypted_value="encrypted(slack_secret)",
        folder="Work",
    )
    password_repository.save(password1)
    password_permissions_repository.set_owner(group1_id, password1.id)
    group_access_gateway.set_group_owner(group1_id, requester_id)
    password_repository.save(password2)
    password_permissions_repository.set_owner(group2_id, password2.id)
    group_access_gateway.set_group_owner(group2_id, requester_id)

    # Add creation events for both passwords
    password_event_repository.append_event(
        event_id=UUID("6acb8c27-7dc7-47dd-9cc9-33b232f27018"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 1, 10, 0, 0),
        password_id=password1.id,
        actor_user_id=requester_id,
        event_data={
            "password_id": str(password1.id),
            "password_name": "Gmail",
            "owner_group_id": str(group1_id),
            "folder": folder_name,
        },
    )
    password_event_repository.append_event(
        event_id=UUID("6acb8c27-7dc7-47dd-9cc9-33b232f2701a"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 2, 10, 0, 0),
        password_id=password2.id,
        actor_user_id=requester_id,
        event_data={
            "password_id": str(password2.id),
            "password_name": "Slack",
            "owner_group_id": str(group2_id),
            "folder": "Work",
        },
    )

    command = ListPasswordsCommand(
        requester=AuthenticatedUser(user_id=requester_id, roles=[]), folder=folder_name
    )
    result = use_case.execute(command)

    assert len(result) == 1
    assert result[0].id == password1.id
    assert result[0].name == password1.name
    assert result[0].folder == password1.folder
    assert result[0].group_id == group1_id


def test_given_non_existent_folder_when_listing_passwords_should_raise_folder_not_found_error(
    use_case: ListPasswordsUseCase,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    folder_name = "NoneExistent"

    command = ListPasswordsCommand(
        requester=AuthenticatedUser(user_id=requester_id, roles=[]), folder=folder_name
    )
    with pytest.raises(FolderNotFoundError) as exc_info:
        use_case.execute(command)

    assert folder_name in str(exc_info.value)


def test_given_mixed_access_when_listing_passwords_should_return_only_accessible_passwords(
    use_case: ListPasswordsUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e6")
    password1 = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(gmail_secret)",
        folder="default",
    )
    password2 = Password(
        id=UUID("55050a52-7dc7-47dd-9cc9-33b232f27018"),
        name="Slack",
        encrypted_value="encrypted(slack_secret)",
        folder="default",
    )

    password_repository.save(password1)
    password_permissions_repository.set_owner(group_id, password1.id)
    group_access_gateway.set_group_owner(group_id, requester_id)
    password_repository.save(password2)
    # Not granting access to password2

    # Add creation event for accessible password
    password_event_repository.append_event(
        event_id=UUID("5cb8c527-7dc7-47dd-9cc9-33b232f27018"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 1, 10, 0, 0),
        password_id=password1.id,
        actor_user_id=requester_id,
        event_data={
            "password_id": str(password1.id),
            "password_name": "Gmail",
            "owner_group_id": str(group_id),
            "folder": "default",
        },
    )

    command = ListPasswordsCommand(
        requester=AuthenticatedUser(user_id=requester_id, roles=[])
    )
    result = use_case.execute(command)

    assert len(result) == 1
    assert result[0].id == password1.id
    assert result[0].name == password1.name
    assert result[0].folder == "default"
    assert result[0].group_id == group_id


def test_given_no_access_to_passwords_when_listing_passwords_should_return_empty_list(
    use_case: ListPasswordsUseCase,
    password_repository: FakePasswordRepository,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    password1 = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(gmail_secret)",
        folder="default",
    )
    password2 = Password(
        id=UUID("55050a52-7dc7-47dd-9cc9-33b232f27018"),
        name="Slack",
        encrypted_value="encrypted(slack_secret)",
        folder="default",
    )

    password_repository.save(password1)
    # Not granting access to password1
    password_repository.save(password2)
    # Not granting access to password2

    command = ListPasswordsCommand(
        requester=AuthenticatedUser(user_id=requester_id, roles=[])
    )
    result = use_case.execute(command)

    assert result == []


def test_given_passwords_owned_by_other_users_when_listing_as_user_with_no_groups_should_return_empty_list(
    use_case: ListPasswordsUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    other_user_id = UUID("9d742e0e-bb76-4728-83ef-8d546d7c62e6")
    other_group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(gmail_secret)",
        folder="default",
    )
    password_repository.save(password)
    password_permissions_repository.set_owner(other_group_id, password.id)
    group_access_gateway.set_group_owner(other_group_id, other_user_id)

    password_event_repository.append_event(
        event_id=UUID("5cb8c527-7dc7-47dd-9cc9-33b232f27018"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 1, 10, 0, 0),
        password_id=password.id,
        actor_user_id=other_user_id,
        event_data={},
    )

    command = ListPasswordsCommand(
        requester=AuthenticatedUser(user_id=requester_id, roles=[])
    )
    result = use_case.execute(command)

    assert result == []


def test_given_passwords_with_creation_events_when_listing_passwords_should_return_timestamps(
    use_case: ListPasswordsUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password1_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")
    password1 = Password(
        id=password1_id,
        name="Gmail",
        encrypted_value="encrypted(gmail_secret)",
        folder="default",
    )
    password_repository.save(password1)
    password_permissions_repository.set_owner(group_id, password1.id)
    group_access_gateway.set_group_owner(group_id, requester_id)

    creation_date1 = datetime(2025, 1, 15, 10, 30, 0)
    password_event_repository.append_event(
        event_id=UUID("a3c8c527-7dc7-47dd-9cc9-33b232f27018"),
        event_type="PasswordCreatedEvent",
        occurred_on=creation_date1,
        password_id=password1_id,
        actor_user_id=requester_id,
        event_data={
            "password_id": str(password1_id),
            "password_name": "Gmail",
            "owner_group_id": str(group_id),
            "folder": "default",
        },
    )

    password2_id = UUID("55050a52-7dc7-47dd-9cc9-33b232f27018")
    password2 = Password(
        id=password2_id,
        name="Slack",
        encrypted_value="encrypted(slack_secret)",
        folder="work",
    )
    password_repository.save(password2)
    password_permissions_repository.set_owner(group_id, password2.id)

    creation_date2 = datetime(2025, 1, 20, 14, 0, 0)
    password_event_repository.append_event(
        event_id=UUID("6acb8c27-7dc7-47dd-9cc9-33b232f2701c"),
        event_type="PasswordCreatedEvent",
        occurred_on=creation_date2,
        password_id=password2_id,
        actor_user_id=requester_id,
        event_data={
            "password_id": str(password2_id),
            "password_name": "Slack",
            "owner_group_id": str(group_id),
            "folder": "work",
        },
    )

    command = ListPasswordsCommand(
        requester=AuthenticatedUser(user_id=requester_id, roles=[])
    )
    result = use_case.execute(command)

    assert len(result) == 2

    password1_result = next(r for r in result if r.id == password1_id)
    assert password1_result.created_at == creation_date1
    assert password1_result.last_password_updated_at == creation_date1

    password2_result = next(r for r in result if r.id == password2_id)
    assert password2_result.created_at == creation_date2
    assert password2_result.last_password_updated_at == creation_date2


def test_given_passwords_with_password_updates_when_listing_passwords_should_return_last_update_date(
    use_case: ListPasswordsUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")
    password = Password(
        id=password_id,
        name="Gmail",
        encrypted_value="encrypted(newsecret)",
        folder="default",
    )
    password_repository.save(password)
    password_permissions_repository.set_owner(group_id, password.id)
    group_access_gateway.set_group_owner(group_id, requester_id)

    creation_date = datetime(2025, 1, 15, 10, 30, 0)
    password_event_repository.append_event(
        event_id=UUID("6acb8c27-7dc7-47dd-9cc9-33b232fc7018"),
        event_type="PasswordCreatedEvent",
        occurred_on=creation_date,
        password_id=password_id,
        actor_user_id=requester_id,
        event_data={
            "password_id": str(password_id),
            "password_name": "Gmail",
            "owner_group_id": str(group_id),
            "folder": "default",
        },
    )

    update_date = datetime(2025, 1, 20, 14, 30, 0)
    password_event_repository.append_event(
        event_id=UUID("0a1b2c3d-4e5f-6789-abcd-ef0123456789"),
        event_type="PasswordUpdatedEvent",
        occurred_on=update_date,
        password_id=password_id,
        actor_user_id=requester_id,
        event_data={
            "password_id": str(password_id),
            "has_name_changed": False,
            "has_password_changed": True,
            "has_folder_changed": False,
        },
    )

    command = ListPasswordsCommand(
        requester=AuthenticatedUser(user_id=requester_id, roles=[])
    )
    result = use_case.execute(command)

    assert len(result) == 1
    assert result[0].created_at == creation_date
    assert result[0].last_password_updated_at == update_date


def test_given_owner_user_when_listing_passwords_should_return_can_read_and_can_write_true(
    use_case: ListPasswordsUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e6")
    password_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    password = Password(
        id=password_id,
        name="Gmail",
        encrypted_value="encrypted(gmail_secret)",
        folder="default",
    )
    password_repository.save(password)
    password_permissions_repository.set_owner(group_id, password_id)
    group_access_gateway.set_group_owner(group_id, requester_id)

    password_event_repository.append_event(
        event_id=UUID("10e2eb69-5d6b-4500-947a-6636c8755b3f"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 1, 10, 0, 0),
        password_id=password_id,
        actor_user_id=requester_id,
        event_data={},
    )

    command = ListPasswordsCommand(
        requester=AuthenticatedUser(user_id=requester_id, roles=[])
    )
    result = use_case.execute(command)

    assert len(result) == 1
    assert result[0].can_read is True
    assert result[0].can_write is True


def test_given_read_only_shared_user_when_listing_passwords_should_return_can_read_true_and_can_write_false(
    use_case: ListPasswordsUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    owner_group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e6")
    shared_group_id = UUID("3d742e0e-bb76-4728-83ef-8d546d7c62e6")
    password_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    password = Password(
        id=password_id,
        name="Gmail",
        encrypted_value="encrypted(gmail_secret)",
        folder="default",
    )
    password_repository.save(password)
    password_permissions_repository.set_owner(owner_group_id, password_id)
    password_permissions_repository.grant_access(
        shared_group_id, password_id, PasswordPermission.READ
    )
    group_access_gateway.set_group_owner(shared_group_id, requester_id)

    password_event_repository.append_event(
        event_id=UUID("10e2eb69-5d6b-4500-947a-6636c8755b3f"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 1, 10, 0, 0),
        password_id=password_id,
        actor_user_id=requester_id,
        event_data={},
    )

    command = ListPasswordsCommand(
        requester=AuthenticatedUser(user_id=requester_id, roles=[])
    )
    result = use_case.execute(command)

    assert len(result) == 1
    assert result[0].can_read is True
    assert result[0].can_write is False


def test_given_admin_user_with_no_group_access_when_listing_passwords_should_return_all_passwords_with_both_permissions_false(
    use_case: ListPasswordsUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
):
    admin_id = UUID("9d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group1_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group2_id = UUID("3d742e0e-bb76-4728-83ef-8d546d7c62e6")
    other_user_id = UUID("4d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password1 = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(gmail_secret)",
        folder="default",
    )
    password2 = Password(
        id=UUID("55050a52-7dc7-47dd-9cc9-33b232f27018"),
        name="Slack",
        encrypted_value="encrypted(slack_secret)",
        folder="Work",
    )

    password_repository.save(password1)
    password_permissions_repository.set_owner(group1_id, password1.id)
    group_access_gateway.set_group_owner(group1_id, other_user_id)

    password_repository.save(password2)
    password_permissions_repository.set_owner(group2_id, password2.id)
    group_access_gateway.set_group_owner(group2_id, other_user_id)

    password_event_repository.append_event(
        event_id=UUID("10e2eb69-5d6b-4500-947a-6636c8755b3f"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 1, 10, 0, 0),
        password_id=password1.id,
        actor_user_id=other_user_id,
        event_data={},
    )
    password_event_repository.append_event(
        event_id=UUID("9fd8c527-7dc7-47dd-9cc9-33b232f27018"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 2, 10, 0, 0),
        password_id=password2.id,
        actor_user_id=other_user_id,
        event_data={},
    )

    command = ListPasswordsCommand(
        requester=AuthenticatedUser(user_id=admin_id, roles=["admin"])
    )
    result = use_case.execute(command)

    assert len(result) == 2
    for r in result:
        assert r.can_read is False
        assert r.can_write is False


def test_given_admin_user_with_group_ownership_when_listing_passwords_should_return_correct_permissions(
    use_case: ListPasswordsUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
):
    admin_id = UUID("9d742e0e-bb76-4728-83ef-8d546d7c62e6")
    admin_group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e6")
    other_group_id = UUID("3d742e0e-bb76-4728-83ef-8d546d7c62e6")
    other_user_id = UUID("4d742e0e-bb76-4728-83ef-8d546d7c62e6")

    admin_password = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(gmail_secret)",
        folder="default",
    )
    other_password = Password(
        id=UUID("55050a52-7dc7-47dd-9cc9-33b232f27018"),
        name="Slack",
        encrypted_value="encrypted(slack_secret)",
        folder="Work",
    )

    password_repository.save(admin_password)
    password_permissions_repository.set_owner(admin_group_id, admin_password.id)
    group_access_gateway.set_group_owner(admin_group_id, admin_id)

    password_repository.save(other_password)
    password_permissions_repository.set_owner(other_group_id, other_password.id)
    group_access_gateway.set_group_owner(other_group_id, other_user_id)

    password_event_repository.append_event(
        event_id=UUID("10e2eb69-5d6b-4500-947a-6636c8755b3f"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 1, 10, 0, 0),
        password_id=admin_password.id,
        actor_user_id=admin_id,
        event_data={},
    )
    password_event_repository.append_event(
        event_id=UUID("9fd8c527-7dc7-47dd-9cc9-33b232f27018"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2025, 1, 2, 10, 0, 0),
        password_id=other_password.id,
        actor_user_id=other_user_id,
        event_data={},
    )

    command = ListPasswordsCommand(
        requester=AuthenticatedUser(user_id=admin_id, roles=["admin"])
    )
    result = use_case.execute(command)

    assert len(result) == 2

    admin_result = next(r for r in result if r.id == admin_password.id)
    assert admin_result.can_read is True
    assert admin_result.can_write is True

    other_result = next(r for r in result if r.id == other_password.id)
    assert other_result.can_read is False
    assert other_result.can_write is False
