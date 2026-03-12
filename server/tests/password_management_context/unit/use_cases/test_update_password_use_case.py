from uuid import UUID

import pytest

from password_management_context.application.commands import UpdatePasswordCommand
from password_management_context.application.use_cases import UpdatePasswordUseCase
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import (
    NotPasswordOwnerError,
    PasswordNotFoundError,
)
from tests.fakes import FakeDomainEventPublisher

from ..fakes import (
    FakeGroupAccessGateway,
    FakePasswordEncryptionGateway,
    FakePasswordEventRepository,
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
)

PASSWORD_ID = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
REQUESTER_ID = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e5")
GROUP_ID = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e6")


@pytest.fixture
def use_case(
    password_repository: FakePasswordRepository,
    password_encryption_gateway: FakePasswordEncryptionGateway,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    domain_event_publisher: FakeDomainEventPublisher,
    password_event_repository: FakePasswordEventRepository,
):
    return UpdatePasswordUseCase(
        password_repository,
        password_encryption_gateway,
        password_permissions_repository,
        group_access_gateway,
        domain_event_publisher,
        password_event_repository,
    )


@pytest.fixture
def stored_password(
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
):
    original = Password(
        id=PASSWORD_ID,
        name="original",
        encrypted_value="encrypted(original)",
        folder="folder",
        login="original_login",
        url="original_url",
    )
    password_repository.save(original)
    password_permissions_repository.set_owner(GROUP_ID, PASSWORD_ID)
    group_access_gateway.set_group_owner(GROUP_ID, REQUESTER_ID)
    return original


def test_given_updated_name_and_password_when_updating_password_should_persist_changes(
    use_case: UpdatePasswordUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
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
    assert password_repository.get_by_id(original_password.id).encrypted_value == "encrypted(updated)"


def test_given_updated_fields_when_updating_password_should_persist_changes(
    use_case: UpdatePasswordUseCase,
    password_repository: FakePasswordRepository,
    stored_password: Password,
):
    command = UpdatePasswordCommand(
        requester_id=REQUESTER_ID,
        id=PASSWORD_ID,
        name="updated",
        password="updated",
        folder="folder",
        login="updated_login",
        url="updated_url",
    )

    use_case.execute(new_password=command)

    saved = password_repository.get_by_id(PASSWORD_ID)
    assert saved.name == "updated"
    assert saved.encrypted_value == "encrypted(updated)"
    assert saved.login == "updated_login"
    assert saved.url == "updated_url"


def test_given_null_login_when_updating_password_should_clear_login(
    use_case: UpdatePasswordUseCase,
    password_repository: FakePasswordRepository,
    stored_password: Password,
):
    command = UpdatePasswordCommand(
        requester_id=REQUESTER_ID,
        id=PASSWORD_ID,
        name="original",
        password="original",
        login=None,
    )

    use_case.execute(new_password=command)

    assert password_repository.get_by_id(PASSWORD_ID).login is None


def test_given_empty_login_when_updating_password_should_clear_login(
    use_case: UpdatePasswordUseCase,
    password_repository: FakePasswordRepository,
    stored_password: Password,
):
    command = UpdatePasswordCommand(
        requester_id=REQUESTER_ID,
        id=PASSWORD_ID,
        name="original",
        password="original",
        login="",
    )

    use_case.execute(new_password=command)

    assert password_repository.get_by_id(PASSWORD_ID).login is None


def test_given_null_url_when_updating_password_should_clear_url(
    use_case: UpdatePasswordUseCase,
    password_repository: FakePasswordRepository,
    stored_password: Password,
):
    command = UpdatePasswordCommand(
        requester_id=REQUESTER_ID,
        id=PASSWORD_ID,
        name="original",
        password="original",
        url=None,
    )

    use_case.execute(new_password=command)

    assert password_repository.get_by_id(PASSWORD_ID).url is None


def test_given_empty_url_when_updating_password_should_clear_url(
    use_case: UpdatePasswordUseCase,
    password_repository: FakePasswordRepository,
    stored_password: Password,
):
    command = UpdatePasswordCommand(
        requester_id=REQUESTER_ID,
        id=PASSWORD_ID,
        name="original",
        password="original",
        url="",
    )

    use_case.execute(new_password=command)

    assert password_repository.get_by_id(PASSWORD_ID).url is None


def test_given_null_folder_when_updating_password_should_set_folder_to_default(
    use_case: UpdatePasswordUseCase,
    password_repository: FakePasswordRepository,
    stored_password: Password,
):
    command = UpdatePasswordCommand(
        requester_id=REQUESTER_ID,
        id=PASSWORD_ID,
        name="original",
        password="original",
        folder=None,
    )

    use_case.execute(new_password=command)

    assert password_repository.get_by_id(PASSWORD_ID).folder == "default"


def test_given_same_values_when_updating_password_should_not_persist_nor_emit_event(
    use_case: UpdatePasswordUseCase,
    password_repository: FakePasswordRepository,
    password_event_repository: FakePasswordEventRepository,
    stored_password: Password,
):
    command = UpdatePasswordCommand(
        requester_id=REQUESTER_ID,
        id=PASSWORD_ID,
        name="original",
        password="original",
        folder="folder",
        login="original_login",
        url="original_url",
    )

    use_case.execute(new_password=command)

    assert password_repository.update_count == 0
    assert len(password_event_repository.events) == 0


def test_given_non_existing_password_when_updating_password_should_raise_password_not_found(
    use_case: UpdatePasswordUseCase,
):
    command = UpdatePasswordCommand(
        requester_id=REQUESTER_ID,
        id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"),
        name="original",
        password="original",
    )

    with pytest.raises(PasswordNotFoundError):
        use_case.execute(command)


def test_given_no_access_when_updating_password_should_raise_not_password_owner_error(
    use_case: UpdatePasswordUseCase,
    password_repository: FakePasswordRepository,
):
    password = Password(
        id=PASSWORD_ID,
        name="original",
        encrypted_value="encrypted(original)",
        folder="folder",
    )
    password_repository.save(password)

    command = UpdatePasswordCommand(
        requester_id=REQUESTER_ID,
        id=PASSWORD_ID,
        name="updated",
        password="updated",
    )

    with pytest.raises(NotPasswordOwnerError):
        use_case.execute(new_password=command)
