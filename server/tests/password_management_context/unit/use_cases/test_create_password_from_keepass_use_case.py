# test_create_password_from_keepass_use_case.py

from uuid import UUID

import pytest

from password_management_context.application.commands.create_password_from_keepass_command import (
    CreatePasswordsFromKeepassCommand,
)
from password_management_context.application.use_cases.create_password_from_keepass_use_case import (
    CreatePasswordsFromKeepassUseCase,
)
from password_management_context.domain.entities.keepass_entry import KeepassEntry
from password_management_context.domain.exceptions import (
    GroupNotFoundError,
    UserNotOwnerOfGroupError,
)
from tests.shared_kernel.fakes import FakeEventPublisher

from ..fakes import (
    FakeGroupAccessGateway,
    FakePasswordEncryptionGateway,
    FakePasswordEventRepository,
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
)


class FakeKeepassReaderGateway:
    def __init__(self):
        self.entries: list[KeepassEntry] = []
        self.received_content: bytes | None = None
        self.received_master_password: str | None = None

    def read_entries(
        self,
        content: bytes,
        master_password: str,
    ) -> list[KeepassEntry]:
        self.received_content = content
        self.received_master_password = master_password
        return self.entries


@pytest.fixture
def keepass_reader_gateway():
    return FakeKeepassReaderGateway()


@pytest.fixture
def use_case(
    password_repository: FakePasswordRepository,
    password_encryption_gateway: FakePasswordEncryptionGateway,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    domain_event_publisher: FakeEventPublisher,
    password_event_repository: FakePasswordEventRepository,
    keepass_reader_gateway: FakeKeepassReaderGateway,
):
    return CreatePasswordsFromKeepassUseCase(
        password_repository,
        password_encryption_gateway,
        password_permissions_repository,
        group_access_gateway,
        domain_event_publisher,
        password_event_repository,
        keepass_reader_gateway,
    )


def test_given_user_owns_group_when_importing_keepass_should_create_passwords(
    use_case,
    password_repository,
    group_access_gateway,
    keepass_reader_gateway,
):
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")

    group_access_gateway.set_group_owner(group_id, user_id)

    keepass_reader_gateway.entries = [
        KeepassEntry(
            title="Github",
            username="github-login",
            password="GithubP@ssw0rd",
            url="https://github.com",
            notes="note",
        ),
        KeepassEntry(
            title="Gmail",
            username="gmail-login",
            password="GmailP@ssw0rd",
            url="https://gmail.com",
            notes=None,
        ),
    ]

    command = CreatePasswordsFromKeepassCommand(
        user_id=user_id,
        group_id=group_id,
        filename="import.kdbx",
        content=b"fake-keepass-content",
        master_password="master-password",
    )

    created_ids = use_case.execute(command)

    assert len(created_ids) == 2

    first_password = password_repository.get_by_id(created_ids[0])
    assert first_password.name == "Github"
    assert first_password.login == "github-login"
    assert first_password.url == "https://github.com"
    assert first_password.encrypted_value == "encrypted(GithubP@ssw0rd)"

    second_password = password_repository.get_by_id(created_ids[1])
    assert second_password.name == "Gmail"
    assert second_password.login == "gmail-login"
    assert second_password.url == "https://gmail.com"
    assert second_password.encrypted_value == "encrypted(GmailP@ssw0rd)"


def test_given_user_owns_group_when_importing_keepass_should_call_reader_with_file_content(
    use_case,
    group_access_gateway,
    keepass_reader_gateway,
):
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")

    group_access_gateway.set_group_owner(group_id, user_id)

    command = CreatePasswordsFromKeepassCommand(
        user_id=user_id,
        group_id=group_id,
        filename="import.kdbx",
        content=b"keepass-content",
        master_password="master-password",
    )

    use_case.execute(command)

    assert keepass_reader_gateway.received_content == b"keepass-content"
    assert keepass_reader_gateway.received_master_password == "master-password"


def test_given_group_not_exists_when_importing_keepass_should_raise_group_not_found_error(
    use_case,
):
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")

    command = CreatePasswordsFromKeepassCommand(
        user_id=user_id,
        group_id=group_id,
        filename="import.kdbx",
        content=b"keepass-content",
        master_password="master-password",
    )

    with pytest.raises(GroupNotFoundError) as exc_info:
        use_case.execute(command)

    assert str(group_id) in str(exc_info.value)


def test_given_user_not_owner_when_importing_keepass_should_raise_user_not_owner_error(
    use_case,
    group_access_gateway,
):
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    other_user_id = UUID("3d742e0e-bb76-4728-83ef-8d546d7c62e8")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")

    group_access_gateway.set_group_owner(group_id, other_user_id)

    command = CreatePasswordsFromKeepassCommand(
        user_id=user_id,
        group_id=group_id,
        filename="import.kdbx",
        content=b"keepass-content",
        master_password="master-password",
    )

    with pytest.raises(UserNotOwnerOfGroupError) as exc_info:
        use_case.execute(command)

    assert str(user_id) in str(exc_info.value)
    assert str(group_id) in str(exc_info.value)


def test_given_valid_keepass_entries_when_importing_should_set_group_as_owner(
    use_case,
    group_access_gateway,
    keepass_reader_gateway,
    password_permissions_repository,
):
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")

    group_access_gateway.set_group_owner(group_id, user_id)

    keepass_reader_gateway.entries = [
        KeepassEntry(
            title="Github",
            username="github-login",
            password="GithubP@ssw0rd",
            url="https://github.com",
            notes=None,
        )
    ]

    command = CreatePasswordsFromKeepassCommand(
        user_id=user_id,
        group_id=group_id,
        filename="import.kdbx",
        content=b"keepass-content",
        master_password="master-password",
    )

    created_ids = use_case.execute(command)

    assert password_permissions_repository.is_owner(group_id, created_ids[0])


def test_given_valid_keepass_entries_when_importing_should_store_password_created_events(
    use_case,
    group_access_gateway,
    keepass_reader_gateway,
    password_event_repository,
):
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    group_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")

    group_access_gateway.set_group_owner(group_id, user_id)

    keepass_reader_gateway.entries = [
        KeepassEntry(
            title="Github",
            username="github-login",
            password="GithubP@ssw0rd",
            url="https://github.com",
            notes=None,
        )
    ]

    command = CreatePasswordsFromKeepassCommand(
        user_id=user_id,
        group_id=group_id,
        filename="import.kdbx",
        content=b"keepass-content",
        master_password="master-password",
    )

    created_ids = use_case.execute(command)

    assert len(password_event_repository.events) == 1
    stored_event = password_event_repository.events[0]
    assert stored_event["event_type"] == "PasswordCreatedEvent"
    assert stored_event["password_id"] == created_ids[0]
    assert stored_event["actor_user_id"] == user_id
    assert str(group_id) in str(stored_event["event_data"]["owner_group_id"])
