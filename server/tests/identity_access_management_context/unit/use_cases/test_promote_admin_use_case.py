import pytest
from uuid import UUID
from identity_access_management_context.application.use_cases import PromoteAdminUseCase
from identity_access_management_context.application.commands import PromoteAdminCommand
from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.events import AdminPromotedEvent
from identity_access_management_context.domain.exceptions import (
    UserAlreadyAdminException,
    UserNotFoundException,
)
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from shared_kernel.domain.entities import AuthenticatedUser
from shared_kernel.domain.value_objects import ADMIN_ROLE
from shared_kernel.adapters.primary.exceptions import NotAdminError


@pytest.fixture
def use_case(user_repository: UserRepository, event_publisher, user_event_repository):
    return PromoteAdminUseCase(user_repository, event_publisher, user_event_repository)


def test_given_admin_user_and_non_admin_target_when_promoting_should_add_admin_role(
    use_case: PromoteAdminUseCase,
    user_repository: UserRepository,
):
    # Arrange
    admin_id = UUID("11111111-1111-1111-1111-111111111111")
    target_user_id = UUID("22222222-2222-2222-2222-222222222222")

    # Create target user (not admin)
    target_user = User(
        id=target_user_id,
        username="targetuser",
        email="target@example.com",
        name="Target User",
        roles=[],
    )
    user_repository.save(target_user)

    # Create requesting user (admin)
    requesting_user = AuthenticatedUser(
        user_id=admin_id,
        roles=[ADMIN_ROLE],
    )

    command = PromoteAdminCommand(
        requesting_user=requesting_user,
        user_id=target_user_id,
    )

    # Act
    use_case.execute(command)

    # Assert
    updated_user = user_repository.get_by_id(target_user_id)
    assert updated_user is not None
    assert ADMIN_ROLE in updated_user.roles


def test_given_non_admin_requesting_user_when_promoting_should_raise_not_admin_error(
    use_case: PromoteAdminUseCase,
    user_repository: UserRepository,
):
    # Arrange
    non_admin_id = UUID("11111111-1111-1111-1111-111111111111")
    target_user_id = UUID("22222222-2222-2222-2222-222222222222")

    # Create target user (not admin)
    target_user = User(
        id=target_user_id,
        username="targetuser",
        email="target@example.com",
        name="Target User",
        roles=[],
    )
    user_repository.save(target_user)

    # Create requesting user (NOT admin)
    requesting_user = AuthenticatedUser(
        user_id=non_admin_id,
        roles=[],
    )

    command = PromoteAdminCommand(
        requesting_user=requesting_user,
        user_id=target_user_id,
    )

    # Act & Assert
    with pytest.raises(NotAdminError):
        use_case.execute(command)


def test_given_user_already_admin_when_promoting_should_raise_user_already_admin_exception(
    use_case: PromoteAdminUseCase,
    user_repository: UserRepository,
):
    # Arrange
    admin_id = UUID("11111111-1111-1111-1111-111111111111")
    target_user_id = UUID("22222222-2222-2222-2222-222222222222")

    # Create target user (already admin)
    target_user = User(
        id=target_user_id,
        username="targetuser",
        email="target@example.com",
        name="Target User",
        roles=[ADMIN_ROLE],
    )
    user_repository.save(target_user)

    # Create requesting user (admin)
    requesting_user = AuthenticatedUser(
        user_id=admin_id,
        roles=[ADMIN_ROLE],
    )

    command = PromoteAdminCommand(
        requesting_user=requesting_user,
        user_id=target_user_id,
    )

    # Act & Assert
    with pytest.raises(UserAlreadyAdminException):
        use_case.execute(command)


def test_given_non_existent_user_when_promoting_should_raise_user_not_found_exception(
    use_case: PromoteAdminUseCase,
    user_repository: UserRepository,
):
    # Arrange
    admin_id = UUID("11111111-1111-1111-1111-111111111111")
    non_existent_user_id = UUID("99999999-9999-9999-9999-999999999999")

    # Create requesting user (admin)
    requesting_user = AuthenticatedUser(
        user_id=admin_id,
        roles=[ADMIN_ROLE],
    )

    command = PromoteAdminCommand(
        requesting_user=requesting_user,
        user_id=non_existent_user_id,
    )

    # Act & Assert
    with pytest.raises(UserNotFoundException):
        use_case.execute(command)


def test_given_admin_user_and_non_admin_target_when_promoting_should_publish_admin_promoted_event(
    use_case: PromoteAdminUseCase,
    user_repository: UserRepository,
    event_publisher: FakeDomainEventPublisher,
):
    admin_id = UUID("11111111-1111-1111-1111-111111111111")
    target_user_id = UUID("22222222-2222-2222-2222-222222222222")

    target_user = User(
        id=target_user_id,
        username="targetuser",
        email="target@example.com",
        name="Target User",
        roles=[],
    )
    user_repository.save(target_user)

    requesting_user = AuthenticatedUser(user_id=admin_id, roles=[ADMIN_ROLE])
    command = PromoteAdminCommand(requesting_user=requesting_user, user_id=target_user_id)

    use_case.execute(command)

    events = event_publisher.get_published_events_of_type(AdminPromotedEvent)
    assert len(events) == 1
    assert events[0].user_id == target_user_id
    assert events[0].promoted_by_user_id == admin_id


def test_given_admin_user_when_promoting_should_store_admin_promoted_event(
    use_case: PromoteAdminUseCase,
    user_repository: UserRepository,
    user_event_repository,
):
    admin_id = UUID("11111111-1111-1111-1111-111111111111")
    target_user_id = UUID("22222222-2222-2222-2222-222222222222")

    target_user = User(
        id=target_user_id,
        username="targetuser",
        email="target@example.com",
        name="Target User",
        roles=[],
    )
    user_repository.save(target_user)

    requesting_user = AuthenticatedUser(user_id=admin_id, roles=[ADMIN_ROLE])
    command = PromoteAdminCommand(requesting_user=requesting_user, user_id=target_user_id)

    use_case.execute(command)

    assert len(user_event_repository.events) == 1
    stored = user_event_repository.events[0]
    assert stored["event_type"] == "AdminPromotedEvent"
    assert stored["actor_user_id"] == admin_id
