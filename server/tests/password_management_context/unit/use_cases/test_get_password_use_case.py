import pytest
from uuid import UUID

from password_management_context.application.commands import GetPasswordCommand
from password_management_context.application.use_cases import GetPasswordUseCase

from ..fakes import (
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
    FakeGroupAccessGateway,
    FakeEncryptionService,
)
from tests.fakes import FakeDomainEventPublisher
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    PasswordAccessDeniedError,
)
from password_management_context.domain.entities import Password
from password_management_context.domain.value_objects import (
    PasswordPermission,
)


@pytest.fixture
def use_case(
    password_repository: FakePasswordRepository,
    encryption_service: FakeEncryptionService,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    domain_event_publisher: FakeDomainEventPublisher,
):
    return GetPasswordUseCase(
        password_repository,
        encryption_service,
        password_permissions_repository,
        group_access_gateway,
        domain_event_publisher,
    )


def test_given_user_with_read_permission_when_getting_password_should_return_decrypted_password(
    use_case: GetPasswordUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    password_entity = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(supersecret)",
        folder="default",
    )
    password_repository.save(password_entity)
    # Grant READ permission to group and set user as owner of group
    password_permissions_repository.grant_access(
        group_id, password_entity.id, PasswordPermission.READ
    )
    group_access_gateway.set_group_owner(group_id, user_id)

    command = GetPasswordCommand(requester_id=user_id, password_id=password_entity.id)
    result = use_case.execute(command)

    assert result.id == password_entity.id
    assert result.name == password_entity.name
    assert result.password == "supersecret"


def test_given_user_without_access_when_getting_password_should_raise_access_denied_error(
    use_case: GetPasswordUseCase,
    password_repository: FakePasswordRepository,
):
    user_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")

    password = Password(
        id=password_id,
        name="name",
        encrypted_value="encrypted(secret123)",
        folder="folder",
    )
    password_repository.save(password)

    command = GetPasswordCommand(requester_id=user_id, password_id=password_id)
    with pytest.raises(PasswordAccessDeniedError):
        use_case.execute(command)


def test_given_password_not_exists_when_getting_password_should_raise_password_not_found_error(
    use_case: GetPasswordUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
):
    user_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")
    non_existent_password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")

    password_permissions_repository.set_owner(user_id, non_existent_password_id)

    command = GetPasswordCommand(
        requester_id=user_id, password_id=non_existent_password_id
    )
    with pytest.raises(PasswordNotFoundError):
        use_case.execute(command)


def test_given_user_is_owner_when_getting_password_should_return_decrypted_password(
    use_case: GetPasswordUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    password_entity = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(supersecret)",
        folder="default",
    )
    password_repository.save(password_entity)
    # Set group as owner and user as owner of group
    password_permissions_repository.set_owner(group_id, password_entity.id)
    group_access_gateway.set_group_owner(group_id, user_id)

    command = GetPasswordCommand(requester_id=user_id, password_id=password_entity.id)
    result = use_case.execute(command)

    assert result.id == password_entity.id
    assert result.name == password_entity.name
    assert result.password == "supersecret"


def test_given_user_is_group_member_when_getting_password_should_return_decrypted_password(
    use_case: GetPasswordUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    password_entity = Password(
        id=UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f"),
        name="Gmail",
        encrypted_value="encrypted(supersecret)",
        folder="default",
    )
    password_repository.save(password_entity)
    group_access_gateway.add_group_member(group_id, user_id)
    password_permissions_repository.grant_access(
        group_id, password_entity.id, PasswordPermission.READ
    )

    command = GetPasswordCommand(requester_id=user_id, password_id=password_entity.id)
    result = use_case.execute(command)

    assert result.id == password_entity.id
    assert result.name == password_entity.name
    assert result.password == "supersecret"
