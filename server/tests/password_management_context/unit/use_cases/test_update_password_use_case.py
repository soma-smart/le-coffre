import pytest
from uuid import UUID

from password_management_context.adapters.secondary.gateways import (
    InMemoryPasswordRepository,
)
from password_management_context.application.use_cases import UpdatePasswordUseCase
from password_management_context.domain.entities import Password
from password_management_context.application.commands import UpdatePasswordCommand
from shared_kernel.access_control.access_controller import AccessController
from shared_kernel.access_control.exceptions import AccessDeniedError


@pytest.fixture
def use_case(
    password_repository, encryption_service, access_controller: AccessController
):
    return UpdatePasswordUseCase(
        password_repository, encryption_service, access_controller
    )


def test_should_update_password(
    use_case: UpdatePasswordUseCase,
    password_repository: InMemoryPasswordRepository,
    access_controller: AccessController,
):
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e5")
    original_password = Password(
        id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"),
        name="original",
        encrypted_value="encrypted(original)",
        folder="folder",
    )
    password_repository.save(original_password)
    access_controller.grant_access(requester_id, original_password.id)

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


# For security purpose, AccessDenied and not PasswordNotFound
def test_when_requesting_a_non_existing_password_should_raise_access_denied(
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

    with pytest.raises(AccessDeniedError):
        use_case.execute(password_data)
