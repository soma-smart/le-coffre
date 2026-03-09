from uuid import UUID

import pytest

from identity_access_management_context.application.commands import AdminLoginCommand
from identity_access_management_context.application.use_cases import (
    PasswordLoginUseCase,
)
from identity_access_management_context.domain.constants import ADMIN_ROLE
from identity_access_management_context.domain.entities import (
    User,
    UserPassword,
)
from identity_access_management_context.domain.events import (
    AdminLoginEvent,
    AdminLoginFailedEvent,
)
from identity_access_management_context.domain.exceptions import (
    AdminNotFoundException,
    InvalidCredentialsException,
)
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher

from ..fakes import (
    FakePasswordHashingGateway,
    FakeTimeGateway,
    FakeTokenGateway,
    FakeUserPasswordRepository,
    FakeUserRepository,
)


@pytest.fixture
def use_case(
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
    token_gateway: FakeTokenGateway,
    time_provider: FakeTimeGateway,
    event_publisher,
    admin_event_repository,
):
    return PasswordLoginUseCase(
        user_password_repository,
        user_repository,
        password_hashing_gateway,
        token_gateway,
        time_provider,
        event_publisher,
        admin_event_repository,
    )


@pytest.mark.asyncio
async def test_should_authenticate_admin_and_return_jwt_token(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)
    user = User(id=user_id, username="admin", email=email, name="Admin User", roles=[ADMIN_ROLE])
    user_repository.save(user)

    token_gateway.set_unique_jwt_part("uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")

    response = await use_case.execute(command)

    assert response.jwt_token == f"jwt_token_for_{user_id}_uniqueness"
    assert response.admin_id == user_id
    assert response.email == email


@pytest.mark.asyncio
async def test_should_raise_exception_for_wrong_password(
    use_case: PasswordLoginUseCase, user_password_repository: FakeUserPasswordRepository
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)

    command = AdminLoginCommand(email=email, password="wrong_password")

    with pytest.raises(InvalidCredentialsException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_should_raise_exception_for_non_existent_admin(
    use_case: PasswordLoginUseCase,
):
    command = AdminLoginCommand(email="nonexistent@lecoffre.com", password="any_password")

    with pytest.raises(AdminNotFoundException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_should_return_refresh_token_on_successful_login(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)
    user = User(id=user_id, username="admin", email=email, name="Admin User", roles=[ADMIN_ROLE])
    user_repository.save(user)

    token_gateway.set_unique_jwt_part("uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")

    response = await use_case.execute(command)

    assert response.refresh_token == f"refresh_token_for_{user_id}_uniqueness"
    assert response.refresh_token != response.jwt_token


@pytest.mark.asyncio
async def test_should_publish_admin_login_event_on_successful_login(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
    event_publisher: FakeDomainEventPublisher,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)
    user = User(id=user_id, username="admin", email=email, name="Admin User", roles=[ADMIN_ROLE])
    user_repository.save(user)
    token_gateway.set_unique_jwt_part("uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")
    await use_case.execute(command)

    events = event_publisher.get_published_events_of_type(AdminLoginEvent)
    assert len(events) == 1
    assert events[0].admin_id == user_id
    assert events[0].email == email


@pytest.mark.asyncio
async def test_should_publish_admin_login_failed_event_on_wrong_password(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    event_publisher: FakeDomainEventPublisher,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)

    command = AdminLoginCommand(email=email, password="wrong_password")
    with pytest.raises(InvalidCredentialsException):
        await use_case.execute(command)

    events = event_publisher.get_published_events_of_type(AdminLoginFailedEvent)
    assert len(events) == 1
    assert events[0].email == email
    assert events[0].reason == "Invalid credentials"


@pytest.mark.asyncio
async def test_should_publish_admin_login_failed_event_on_non_existent_admin(
    use_case: PasswordLoginUseCase,
    event_publisher: FakeDomainEventPublisher,
):
    command = AdminLoginCommand(email="nonexistent@lecoffre.com", password="any_password")
    with pytest.raises(AdminNotFoundException):
        await use_case.execute(command)

    events = event_publisher.get_published_events_of_type(AdminLoginFailedEvent)
    assert len(events) == 1
    assert events[0].email == "nonexistent@lecoffre.com"
    assert events[0].reason == "User not found"


@pytest.mark.asyncio
async def test_should_store_admin_login_event_on_successful_login(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
    admin_event_repository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)
    user = User(id=user_id, username="admin", email=email, name="Admin User", roles=[ADMIN_ROLE])
    user_repository.save(user)
    token_gateway.set_unique_jwt_part("uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")
    await use_case.execute(command)

    assert len(admin_event_repository.events) == 1
    stored = admin_event_repository.events[0]
    assert stored["event_type"] == "AdminLoginEvent"
    assert stored["actor_user_id"] == user_id


@pytest.mark.asyncio
async def test_should_store_admin_login_failed_event_on_wrong_password(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    admin_event_repository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)

    command = AdminLoginCommand(email=email, password="wrong_password")
    with pytest.raises(InvalidCredentialsException):
        await use_case.execute(command)

    assert len(admin_event_repository.events) == 1
    stored = admin_event_repository.events[0]
    assert stored["event_type"] == "AdminLoginFailedEvent"
    assert stored["actor_user_id"] is None


@pytest.mark.asyncio
async def test_should_store_admin_login_failed_event_on_non_existent_admin(
    use_case: PasswordLoginUseCase,
    admin_event_repository,
):
    command = AdminLoginCommand(email="nonexistent@lecoffre.com", password="any_password")
    with pytest.raises(AdminNotFoundException):
        await use_case.execute(command)

    assert len(admin_event_repository.events) == 1
    stored = admin_event_repository.events[0]
    assert stored["event_type"] == "AdminLoginFailedEvent"
    assert stored["actor_user_id"] is None


@pytest.mark.asyncio
async def test_given_admin_user_when_logging_in_should_receive_token_with_admin_role(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
):
    user_id = UUID("1a2b3c4d-0000-0000-0000-aabbccddeeff")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(adminpass!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)
    user = User(id=user_id, username="admin", email=email, name="Admin User", roles=[ADMIN_ROLE])
    user_repository.save(user)

    token_gateway.set_unique_jwt_part("uniqueness")
    command = AdminLoginCommand(email=email, password="adminpass!")
    await use_case.execute(command)

    assert token_gateway.last_generated_token is not None
    assert token_gateway.last_generated_token.roles == [ADMIN_ROLE]


@pytest.mark.asyncio
async def test_given_regular_user_when_logging_in_should_receive_token_with_empty_roles(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
):
    """
    Regression test: previously PasswordLoginUseCase (formerly AdminLoginUseCase) hardcoded roles=[ADMIN_ROLE] for
    every user. This meant a regular (non-admin) user would receive an admin JWT,
    allowing them to see all passwords. The fix looks up the user's actual roles.
    """
    user_id = UUID("deadbeef-1234-5678-abcd-000000000001")
    email = "user@lecoffre.com"
    password_hash = b"hashed(userpass!)"

    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash=password_hash,
        display_name="Regular User",
    )
    user_password_repository.save(user_password)
    user = User(id=user_id, username="regularuser", email=email, name="Regular User", roles=[])
    user_repository.save(user)

    token_gateway.set_unique_jwt_part("uniqueness")
    command = AdminLoginCommand(email=email, password="userpass!")
    await use_case.execute(command)

    assert token_gateway.last_generated_token is not None
    assert token_gateway.last_generated_token.roles == []
    assert ADMIN_ROLE not in token_gateway.last_generated_token.roles
