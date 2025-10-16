import pytest
from uuid import UUID

from password_management_context.application.use_cases import DeletePasswordUseCase
from password_management_context.adapters.secondary.gateways import (
    InMemoryPasswordRepository,
)
from password_management_context.domain.exceptions import PasswordNotFoundError
from password_management_context.domain.entities import Password
from tests.fakes import FakeAccessController
from shared_kernel.access_control.access_controller import AccessController


@pytest.fixture
def use_case(password_repository, access_controller: FakeAccessController):
    return DeletePasswordUseCase(password_repository, access_controller)


def test_given_delete_access_when_deleting_should_success(
    use_case: DeletePasswordUseCase,
    password_repository: InMemoryPasswordRepository,
    access_controller: FakeAccessController,
):
    requester_user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    name = "name"
    folder = "folder"
    encrypted_password = "encrypted(secret123)"

    password = Password(
        id=uuid,
        name=name,
        encrypted_value=encrypted_password,
        folder=folder,
    )
    password_repository.save(password)
    access_controller.grant_delete_access(requester_user_id, password.id)

    use_case.execute(requester_user_id, uuid)

    with pytest.raises(PasswordNotFoundError):
        password_repository.get_by_id(uuid)


def test_sould_raise_error_when_password_does_not_exist(
    use_case: DeletePasswordUseCase,
):
    requester_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    fake_resource_uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    with pytest.raises(PasswordNotFoundError):
        use_case.execute(requester_id, fake_resource_uuid)


def test_given_no_access_when_deleting_should_fail(
    use_case: DeletePasswordUseCase, password_repository: InMemoryPasswordRepository
):
    requester_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    resource = Password(
        id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"),
        name="MyPassword",
        encrypted_value="encrypted(MyPassword)",
        folder="folder",
    )
    password_repository.save(resource)

    with pytest.raises(PasswordNotFoundError):
        use_case.execute(requester_id, resource.id)
