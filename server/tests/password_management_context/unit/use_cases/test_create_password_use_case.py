import pytest
from uuid import UUID

from password_management_context.application.gateways import PasswordRepository
from password_management_context.application.commands import CreatePasswordCommand
from password_management_context.application.use_cases import CreatePasswordUseCase


@pytest.fixture
def use_case(password_repository, encryption_service):
    return CreatePasswordUseCase(password_repository, encryption_service)


def test_should_create_password_with_uuid_and_store_encrypted(
    use_case: CreatePasswordUseCase, password_repository: PasswordRepository
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    name = "name"
    decrypted_password = "secret123"
    expected_encrypted = "encrypted(secret123)"

    command = CreatePasswordCommand(
        id=uuid, name=name, decrypted_password=decrypted_password
    )

    password_id = use_case.execute(command)

    assert password_id == uuid

    saved_password = password_repository.get_by_id(password_id)
    assert saved_password.id == uuid
    assert saved_password.name == name
    assert saved_password.encrypted_value == expected_encrypted
    assert saved_password.folder is None


def test_should_create_password_in_folder_with_encrypted_value(
    use_case: CreatePasswordUseCase, password_repository: PasswordRepository
):
    uuid = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    folder = "Work"
    name = "Slack"
    decrypted_password = "work_secret"
    expected_encrypted = "encrypted(work_secret)"

    command = CreatePasswordCommand(
        id=uuid, name=name, decrypted_password=decrypted_password, folder=folder
    )

    password_id = use_case.execute(command)

    assert password_id == uuid
    saved_password = password_repository.get_by_id(password_id)
    assert saved_password.name == name
    assert saved_password.folder == folder
    assert saved_password.encrypted_value == expected_encrypted
