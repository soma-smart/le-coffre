import pytest
from uuid import UUID

from password_management_context.application.commands import ListPasswordsCommand
from password_management_context.application.use_cases import ListPasswordsUseCase

from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import FolderNotFoundError
from ..fakes import (
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
    FakeGroupAccessGateway,
)
from password_management_context.domain.value_objects import PasswordPermission


@pytest.fixture
def use_case(
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
):
    return ListPasswordsUseCase(
        password_repository, password_permissions_repository, group_access_gateway
    )


def test_given_no_passwords_when_listing_default_folder_should_return_empty_list(
    use_case: ListPasswordsUseCase,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")

    command = ListPasswordsCommand(requester_id=requester_id)
    result = use_case.execute(command)

    assert result == []


def test_given_passwords_exist_when_listing_all_folders_should_return_all_accessible_passwords(
    use_case: ListPasswordsUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
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

    command = ListPasswordsCommand(requester_id=requester_id)
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

    command = ListPasswordsCommand(requester_id=requester_id, folder=folder_name)
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

    command = ListPasswordsCommand(requester_id=requester_id, folder=folder_name)
    with pytest.raises(FolderNotFoundError) as exc_info:
        use_case.execute(command)

    assert folder_name in str(exc_info.value)


def test_given_mixed_access_when_listing_passwords_should_return_only_accessible_passwords(
    use_case: ListPasswordsUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
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

    command = ListPasswordsCommand(requester_id=requester_id)
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

    command = ListPasswordsCommand(requester_id=requester_id)
    result = use_case.execute(command)

    assert result == []
