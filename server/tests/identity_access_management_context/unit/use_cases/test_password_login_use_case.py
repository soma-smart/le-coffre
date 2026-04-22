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
    AccountLockedException,
    AdminNotFoundException,
    InvalidCredentialsException,
)

from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from tests.shared_kernel.fakes import FakeTimeGateway

from ..fakes import (
    FakeLoginLockoutGateway,
    FakePasswordHashingGateway,
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
    login_lockout_gateway: FakeLoginLockoutGateway,
):
    return PasswordLoginUseCase(
        user_password_repository,
        user_repository,
        password_hashing_gateway,
        token_gateway,
        time_provider,
        event_publisher,
        admin_event_repository,
        login_lockout_gateway,
    )


@pytest.mark.asyncio
async def test_should_authenticate_admin_and_return_jwt_token(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
    login_lockout_gateway: FakeLoginLockoutGateway,
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
    # A successful login clears any failure state the lockout gateway was tracking.
    assert login_lockout_gateway.successful_login_calls == [email]
    assert login_lockout_gateway.failed_login_calls == []


@pytest.mark.asyncio
async def test_should_raise_exception_for_wrong_password(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    login_lockout_gateway: FakeLoginLockoutGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)

    command = AdminLoginCommand(email=email, password="wrong_password")

    with pytest.raises(InvalidCredentialsException):
        await use_case.execute(command)

    assert login_lockout_gateway.failed_login_calls == [email]


@pytest.mark.asyncio
async def test_should_raise_exception_for_non_existent_admin(
    use_case: PasswordLoginUseCase,
    login_lockout_gateway: FakeLoginLockoutGateway,
):
    command = AdminLoginCommand(email="nonexistent@lecoffre.com", password="any_password")

    with pytest.raises(AdminNotFoundException):
        await use_case.execute(command)

    assert login_lockout_gateway.failed_login_calls == ["nonexistent@lecoffre.com"]


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


# ── Login-lockout behavior ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_given_locked_email_when_logging_in_should_raise_account_locked_exception(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    login_lockout_gateway: FakeLoginLockoutGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    user_password_repository.save(
        UserPassword(id=user_id, email=email, password_hash=b"hashed(secure123!)", display_name="Admin User"),
    )
    login_lockout_gateway.force_lock(email, retry_after=42)

    command = AdminLoginCommand(email=email, password="secure123!")

    with pytest.raises(AccountLockedException) as excinfo:
        await use_case.execute(command)

    assert excinfo.value.retry_after_seconds == 42


@pytest.mark.asyncio
async def test_given_locked_email_when_logging_in_should_not_call_password_verification(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
    login_lockout_gateway: FakeLoginLockoutGateway,
):
    """Regression: the lockout gate runs before ``_lookup_and_verify`` so
    ``bcrypt.verify`` is never invoked during an active lockout. If this test
    fails, the locked-401 path's latency differs from the invalid-credentials
    path's — an account-enumeration oracle."""
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    user_password_repository.save(
        UserPassword(id=user_id, email=email, password_hash=b"hashed(secure123!)", display_name="Admin User"),
    )
    login_lockout_gateway.force_lock(email, retry_after=10)
    assert password_hashing_gateway.verify_calls == []

    with pytest.raises(AccountLockedException):
        await use_case.execute(AdminLoginCommand(email=email, password="secure123!"))

    assert password_hashing_gateway.verify_calls == []


@pytest.mark.asyncio
async def test_given_locked_email_when_logging_in_should_not_record_a_new_failed_login(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    login_lockout_gateway: FakeLoginLockoutGateway,
):
    """A locked attempt does not extend the lock — the gate short-circuits before
    the failure-recording branches in ``_lookup_and_verify`` can fire."""
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    user_password_repository.save(
        UserPassword(id=user_id, email=email, password_hash=b"hashed(secure123!)", display_name="Admin User"),
    )
    login_lockout_gateway.force_lock(email, retry_after=30)

    with pytest.raises(AccountLockedException):
        await use_case.execute(AdminLoginCommand(email=email, password="secure123!"))

    assert login_lockout_gateway.failed_login_calls == []
    assert login_lockout_gateway.successful_login_calls == []
