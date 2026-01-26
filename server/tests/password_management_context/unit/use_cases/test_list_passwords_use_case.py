import pytest
from uuid import UUID

from password_management_context.application.use_cases import ListPasswordsUseCase
from password_management_context.adapters.secondary import (
    InMemoryPasswordRepository,
)
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import FolderNotFoundError
from password_management_context.application.gateways import (
    PasswordPermissionsRepository,
)
from password_management_context.domain.value_objects import PasswordPermission
from password_management_context.domain.events import PasswordsListedEvent


@pytest.fixture
def use_case(
    password_repository,
    password_access_service,
    event_publisher,
):
    return ListPasswordsUseCase(
        password_repository,
        password_access_service,
        event_publisher,
    )


def test_should_return_empty_list_on_default_folder_when_no_passwords(
    use_case: ListPasswordsUseCase,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    result = use_case.execute(requester_id=requester_id)

    assert result == []


def test_should_return_all_passwords_when_no_folder_when_passwords_exist(
    use_case: ListPasswordsUseCase,
    password_repository: InMemoryPasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway,
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

    result = use_case.execute(requester_id=requester_id)

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


def test_should_return_passwords_from_specific_folder_when_folder_provided(
    use_case: ListPasswordsUseCase,
    password_repository: InMemoryPasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway,
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

    result = use_case.execute(requester_id=requester_id, folder=folder_name)

    assert len(result) == 1
    assert result[0].id == password1.id
    assert result[0].name == password1.name
    assert result[0].folder == password1.folder
    assert result[0].group_id == group1_id


def test_should_raise_exception_when_folder_does_not_exist(
    use_case: ListPasswordsUseCase,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    folder_name = "NoneExistent"
    with pytest.raises(FolderNotFoundError) as exc_info:
        use_case.execute(requester_id=requester_id, folder=folder_name)

    assert folder_name in str(exc_info.value)


def test_should_return_only_passwords_user_has_access_to(
    use_case: ListPasswordsUseCase,
    password_repository: InMemoryPasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway,
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

    result = use_case.execute(requester_id=requester_id)

    assert len(result) == 1
    assert result[0].id == password1.id
    assert result[0].name == password1.name
    assert result[0].folder == "default"
    assert result[0].group_id == group_id


def test_should_return_empty_list_when_no_passwords_user_has_access_to(
    use_case: ListPasswordsUseCase,
    password_repository: InMemoryPasswordRepository,
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

    result = use_case.execute(requester_id=requester_id)

    assert result == []


def test_should_publish_passwords_listed_event_when_passwords_are_listed(
    use_case: ListPasswordsUseCase,
    password_repository: InMemoryPasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway,
    event_publisher,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group1_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group2_id = UUID("3d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password1 = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(gmail_secret)",
        folder="work",
    )
    password2 = Password(
        id=UUID("f1f2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Slack",
        encrypted_value="encrypted(slack_secret)",
        folder="work",
    )

    password_repository.save(password1)
    password_repository.save(password2)
    password_permissions_repository.set_owner(group1_id, password1.id)
    password_permissions_repository.set_owner(group2_id, password2.id)
    group_access_gateway.set_group_owner(group1_id, requester_id)
    group_access_gateway.set_group_owner(group2_id, requester_id)

    use_case.execute(requester_id=requester_id, folder="work")

    published_events = event_publisher.published_events
    assert len(published_events) == 1
    event = published_events[0]
    assert isinstance(event, PasswordsListedEvent)
    assert event.listed_by_user_id == requester_id
    assert event.folder == "work"
    assert event.count == 2
    assert event.priority == "LOW"
