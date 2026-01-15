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


@pytest.fixture
def use_case(password_repository, password_permissions_repository):
    return ListPasswordsUseCase(password_repository, password_permissions_repository)


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
        folder="Personal",
    )

    password_repository.save(password1)
    password_permissions_repository.set_owner(requester_id, password1.id)
    password_repository.save(password2)
    password_permissions_repository.grant_access(
        requester_id, password2.id, PasswordPermission.READ
    )

    result = use_case.execute(requester_id=requester_id)

    assert len(result) == 2

    for i in result:
        assert any(
            p.id == i.id and p.name == i.name and p.folder == i.folder
            for p in [password1, password2]
        )


def test_should_return_passwords_from_specific_folder_when_folder_provided(
    use_case: ListPasswordsUseCase,
    password_repository: InMemoryPasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
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
    password_permissions_repository.set_owner(requester_id, password1.id)
    password_repository.save(password2)
    password_permissions_repository.set_owner(requester_id, password2.id)

    result = use_case.execute(requester_id=requester_id, folder=folder_name)

    assert len(result) == 1
    assert result[0].id == password1.id
    assert result[0].name == password1.name
    assert result[0].folder == password1.folder


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
    password_permissions_repository.set_owner(requester_id, password1.id)
    password_repository.save(password2)
    # Not granting access to password2

    result = use_case.execute(requester_id=requester_id)

    assert len(result) == 1
    assert result[0].id == password1.id
    assert result[0].name == password1.name
    assert result[0].folder == "default"


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
