from uuid import UUID, uuid4

import pytest

from identity_access_management_context.application.commands import (
    RegisterAdminWithPasswordCommand,
)
from identity_access_management_context.application.use_cases import (
    RegisterAdminWithPasswordUseCase,
)
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.events import AdminRegisteredEvent
from identity_access_management_context.domain.exceptions import (
    AdminAlreadyExistsException,
)
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher

from ..fakes import (
    FakeGroupMemberRepository,
    FakeGroupRepository,
    FakePasswordHashingGateway,
    FakeUserPasswordRepository,
    FakeUserRepository,
)


@pytest.fixture
def use_case(
    user_password_repository: FakeUserPasswordRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    event_publisher,
    admin_event_repository,
):
    return RegisterAdminWithPasswordUseCase(
        user_password_repository,
        password_hashing_gateway,
        user_repository,
        group_repository,
        group_member_repository,
        event_publisher,
        admin_event_repository,
    )


@pytest.mark.asyncio
async def test_should_register_first_admin_with_password_and_return_user_id(
    use_case: RegisterAdminWithPasswordUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password = "secure123!"
    display_name = "Admin User"

    command = RegisterAdminWithPasswordCommand(id=user_id, email=email, password=password, display_name=display_name)

    result = await use_case.execute(command)

    assert result == user_id

    saved_user_password = user_password_repository.get_by_id(user_id)

    assert saved_user_password
    assert saved_user_password.id == user_id
    assert saved_user_password.email == email
    assert saved_user_password.display_name == display_name
    assert saved_user_password.password_hash == b"hashed(secure123!)"

    # Verify admin was created in user repository with admin role
    saved_user = user_repository.get_by_id(user_id)
    assert saved_user is not None
    assert "admin" in saved_user.roles


@pytest.mark.asyncio
async def test_should_raise_exception_when_admin_already_exists(
    use_case: RegisterAdminWithPasswordUseCase, user_repository: FakeUserRepository
):
    # First create an admin
    existing_admin_id = uuid4()
    existing_admin = User(
        id=existing_admin_id,
        username="existingadmin",
        email="existing@lecoffre.com",
        name="Existing Admin",
        roles=["admin"],
    )
    user_repository.save(existing_admin)

    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    command = RegisterAdminWithPasswordCommand(
        id=user_id,
        email="new@lecoffre.com",
        password="secure123!",
        display_name="New Admin",
    )

    with pytest.raises(AdminAlreadyExistsException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_should_hash_password_before_storing_credentials(
    use_case: RegisterAdminWithPasswordUseCase,
    user_password_repository: FakeUserPasswordRepository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    plain_password = "my_plain_password"
    display_name = "Admin User"

    command = RegisterAdminWithPasswordCommand(
        id=user_id, email=email, password=plain_password, display_name=display_name
    )

    await use_case.execute(command)

    saved_user_password = user_password_repository.get_by_id(user_id)

    assert saved_user_password
    assert saved_user_password.password_hash == b"hashed(my_plain_password)"
    assert saved_user_password.password_hash != plain_password


@pytest.mark.asyncio
async def test_should_delegate_admin_creation_to_user_management_context(
    use_case: RegisterAdminWithPasswordUseCase, user_repository: FakeUserRepository
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    display_name = "Admin User"

    command = RegisterAdminWithPasswordCommand(
        id=user_id, email=email, password="password123", display_name=display_name
    )

    await use_case.execute(command)

    # Verify user was created in user repository
    created_user = user_repository.get_by_id(user_id)
    assert created_user is not None
    assert created_user.id == user_id
    assert created_user.email == email
    assert created_user.name == display_name
    assert "admin" in created_user.roles


@pytest.mark.asyncio
async def test_should_publish_admin_registered_event_on_successful_registration(
    use_case: RegisterAdminWithPasswordUseCase,
    event_publisher: FakeDomainEventPublisher,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"

    command = RegisterAdminWithPasswordCommand(
        id=user_id, email=email, password="secure123!", display_name="Admin User"
    )

    await use_case.execute(command)

    events = event_publisher.get_published_events_of_type(AdminRegisteredEvent)
    assert len(events) == 1
    assert events[0].admin_id == user_id
    assert events[0].email == email


@pytest.mark.asyncio
async def test_should_store_admin_registered_event_on_successful_registration(
    use_case: RegisterAdminWithPasswordUseCase,
    admin_event_repository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"

    command = RegisterAdminWithPasswordCommand(
        id=user_id, email=email, password="secure123!", display_name="Admin User"
    )

    await use_case.execute(command)

    assert len(admin_event_repository.events) == 1
    stored = admin_event_repository.events[0]
    assert stored["event_type"] == "AdminRegisteredEvent"
    assert stored["actor_user_id"] == user_id
