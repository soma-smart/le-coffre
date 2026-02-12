import pytest
from uuid import UUID

from identity_access_management_context.application.use_cases import AdminLoginUseCase
from identity_access_management_context.application.commands import AdminLoginCommand
from identity_access_management_context.domain.entities import (
    UserPassword,
)
from identity_access_management_context.domain.events import AdminLoginEvent, AdminLoginFailedEvent
from identity_access_management_context.domain.exceptions import (
    InvalidCredentialsException,
    AdminNotFoundException,
)
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from ..fakes import (
    FakeUserPasswordRepository,
    FakePasswordHashingGateway,
    FakeTokenGateway,
    FakeTimeGateway,
)


@pytest.fixture
def use_case(
    user_password_repository: FakeUserPasswordRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
    token_gateway: FakeTokenGateway,
    time_provider: FakeTimeGateway,
    event_publisher,
    iam_event_repository,
):
    return AdminLoginUseCase(
        user_password_repository,
        password_hashing_gateway,
        token_gateway,
        time_provider,
        event_publisher,
        iam_event_repository,
    )


@pytest.mark.asyncio
async def test_should_authenticate_admin_and_return_jwt_token(
    use_case: AdminLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    token_gateway: FakeTokenGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(
        id=user_id, email=email, password_hash=password_hash, display_name="Admin User"
    )
    user_password_repository.save(user_password)

    token_gateway.set_unique_jwt_part("uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")

    response = await use_case.execute(command)

    assert response.jwt_token == f"jwt_token_for_{user_id}_uniqueness"
    assert response.admin_id == user_id
    assert response.email == email


@pytest.mark.asyncio
async def test_should_raise_exception_for_wrong_password(
    use_case: AdminLoginUseCase, user_password_repository: FakeUserPasswordRepository
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(
        id=user_id, email=email, password_hash=password_hash, display_name="Admin User"
    )
    user_password_repository.save(user_password)

    command = AdminLoginCommand(email=email, password="wrong_password")

    with pytest.raises(InvalidCredentialsException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_should_raise_exception_for_non_existent_admin(
    use_case: AdminLoginUseCase,
):
    command = AdminLoginCommand(
        email="nonexistent@lecoffre.com", password="any_password"
    )

    with pytest.raises(AdminNotFoundException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_should_return_refresh_token_on_successful_login(
    use_case: AdminLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    token_gateway: FakeTokenGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(
        id=user_id, email=email, password_hash=password_hash, display_name="Admin User"
    )
    user_password_repository.save(user_password)

    token_gateway.set_unique_jwt_part("uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")

    response = await use_case.execute(command)

    assert response.refresh_token == f"refresh_token_for_{user_id}_uniqueness"
    assert response.refresh_token != response.jwt_token


@pytest.mark.asyncio
async def test_should_publish_admin_login_event_on_successful_login(
    use_case: AdminLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    token_gateway: FakeTokenGateway,
    event_publisher: FakeDomainEventPublisher,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(
        id=user_id, email=email, password_hash=password_hash, display_name="Admin User"
    )
    user_password_repository.save(user_password)
    token_gateway.set_unique_jwt_part("uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")
    await use_case.execute(command)

    events = event_publisher.get_published_events_of_type(AdminLoginEvent)
    assert len(events) == 1
    assert events[0].admin_id == user_id
    assert events[0].email == email


@pytest.mark.asyncio
async def test_should_publish_admin_login_failed_event_on_wrong_password(
    use_case: AdminLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    event_publisher: FakeDomainEventPublisher,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(
        id=user_id, email=email, password_hash=password_hash, display_name="Admin User"
    )
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
    use_case: AdminLoginUseCase,
    event_publisher: FakeDomainEventPublisher,
):
    command = AdminLoginCommand(email="nonexistent@lecoffre.com", password="any_password")
    with pytest.raises(AdminNotFoundException):
        await use_case.execute(command)

    events = event_publisher.get_published_events_of_type(AdminLoginFailedEvent)
    assert len(events) == 1
    assert events[0].email == "nonexistent@lecoffre.com"
    assert events[0].reason == "User not found"
