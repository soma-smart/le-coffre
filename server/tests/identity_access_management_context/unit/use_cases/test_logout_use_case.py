import pytest
from uuid import UUID

from identity_access_management_context.application.use_cases import LogoutUseCase
from identity_access_management_context.domain.events import UserLoggedOutEvent
from shared_kernel.domain.entities import ValidatedUser
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from ..fakes import FakeTokenGateway, FakeAdminEventRepository


@pytest.fixture
def use_case(
    token_gateway: FakeTokenGateway,
    event_publisher: FakeDomainEventPublisher,
    admin_event_repository: FakeAdminEventRepository,
):
    return LogoutUseCase(
        token_gateway=token_gateway,
        event_publisher=event_publisher,
        admin_event_repository=admin_event_repository,
    )


def make_validated_user(user_id: UUID, email: str) -> ValidatedUser:
    return ValidatedUser(
        user_id=user_id,
        email=email,
        display_name="Test User",
        roles=["admin"],
    )


@pytest.mark.asyncio
async def test_given_valid_refresh_token_when_logout_then_token_is_revoked(
    use_case: LogoutUseCase,
    token_gateway: FakeTokenGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@example.com"
    refresh_token = "valid_refresh_token_abc"

    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, ["admin"])

    # Verify token is valid before logout
    assert await token_gateway.validate_refresh_token(refresh_token) is not None

    current_user = make_validated_user(user_id, email)
    await use_case.execute(current_user=current_user, refresh_token=refresh_token)

    # Token must be invalidated after logout
    assert await token_gateway.validate_refresh_token(refresh_token) is None
    assert refresh_token in token_gateway.revoked_refresh_tokens


@pytest.mark.asyncio
async def test_given_no_refresh_token_when_logout_then_succeeds_without_error(
    use_case: LogoutUseCase,
    token_gateway: FakeTokenGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@example.com"
    current_user = make_validated_user(user_id, email)

    # Should not raise even when no refresh token is provided
    await use_case.execute(current_user=current_user, refresh_token=None)

    assert len(token_gateway.revoked_refresh_tokens) == 0


@pytest.mark.asyncio
async def test_given_user_when_logout_then_publishes_user_logged_out_event(
    use_case: LogoutUseCase,
    event_publisher: FakeDomainEventPublisher,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@example.com"
    current_user = make_validated_user(user_id, email)

    await use_case.execute(current_user=current_user, refresh_token=None)

    events = event_publisher.get_published_events_of_type(UserLoggedOutEvent)
    assert len(events) == 1
    assert events[0].user_id == user_id
    assert events[0].email == email


@pytest.mark.asyncio
async def test_given_user_when_logout_then_stores_audit_event(
    use_case: LogoutUseCase,
    admin_event_repository: FakeAdminEventRepository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@example.com"
    current_user = make_validated_user(user_id, email)

    await use_case.execute(current_user=current_user, refresh_token=None)

    assert len(admin_event_repository.events) == 1
    stored = admin_event_repository.events[0]
    assert stored["event_type"] == "UserLoggedOutEvent"
    assert stored["actor_user_id"] == user_id
    assert stored["event_data"]["email"] == email
