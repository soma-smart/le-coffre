import pytest
from uuid import UUID

from password_management_context.application.use_cases import UpdatePasswordUseCase
from password_management_context.domain.entities import Password
from password_management_context.application.commands import UpdatePasswordCommand
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    NotPasswordOwnerError,
)
from ..fakes import (
    FakePasswordRepository,
    FakeEncryptionService,
    FakePasswordPermissionsRepository,
    FakeGroupAccessGateway,
)


@pytest.fixture
def use_case(
    password_repository: FakePasswordRepository,
    encryption_service: FakeEncryptionService,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
):
    return UpdatePasswordUseCase(
        password_repository,
        encryption_service,
        password_permissions_repository,
        group_access_gateway,
    )


def test_given_valid_update_data_when_updating_password_should_persist_changes(
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
    assert (
        password_repository.get_by_id(original_password.id).encrypted_value
        == "encrypted(updated)"
    )


# For security purpose, PasswordNotFound and AccessDenied are indistinguishable
def test_given_non_existing_password_when_updating_password_should_raise_password_not_found(
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


def test_given_no_access_when_updating_password_should_raise_not_password_owner_error(
    use_case: UpdatePasswordUseCase,
    password_repository: FakePasswordRepository,
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


def test_given_no_changes_when_updating_password_should_keep_original_values(
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
    )

    use_case.execute(new_password=updated_password)

    stored_password = password_repository.get_by_id(original_password.id)

    assert stored_password.name == "original"
    assert stored_password.encrypted_value == "encrypted(original)"
    assert stored_password.folder == "folder"
