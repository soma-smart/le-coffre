import pytest
from uuid import UUID

from identity_access_management_context.application.use_cases import (
    UpdateUserPasswordUseCase,
)
from identity_access_management_context.application.commands import (
    UpdateUserPasswordCommand,
)
from identity_access_management_context.domain.entities import UserPassword
from identity_access_management_context.domain.events import UserPasswordChangedEvent
from identity_access_management_context.domain.exceptions import (
    InvalidCredentialsException,
    UserNotFoundException,
)
from tests.fakes import FakeDomainEventPublisher
from tests.identity_access_management_context.unit.fakes import (
    FakeUserPasswordRepository,
    FakePasswordHashingGateway,
    FakeUserEventRepository,
)


@pytest.fixture
def use_case(
    user_password_repository: FakeUserPasswordRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
    domain_event_publisher: FakeDomainEventPublisher,
    user_event_repository: FakeUserEventRepository,
):
    return UpdateUserPasswordUseCase(
        user_password_repository,
        password_hashing_gateway,
        domain_event_publisher,
        user_event_repository,
    )


def test_given_valid_user_with_correct_old_password_when_updating_password_should_update_successfully(
    use_case: UpdateUserPasswordUseCase,
    user_password_repository: FakeUserPasswordRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    old_password = "OldPassword123!"
    new_password = "NewPassword456!"

    # Create existing user with hashed old password
    user_password = UserPassword(
        id=user_id,
        email="user@example.com",
        password_hash=password_hashing_gateway.hash(old_password),
        display_name="Test User",
    )
    user_password_repository.save(user_password)

    command = UpdateUserPasswordCommand(
        user_id=user_id,
        old_password=old_password,
        new_password=new_password,
    )

    # Act
    use_case.execute(command)

    # Assert
    updated_user = user_password_repository.get_by_id(user_id)
    assert updated_user is not None
    assert password_hashing_gateway.verify(new_password, updated_user.password_hash)
    assert not password_hashing_gateway.verify(old_password, updated_user.password_hash)


def test_given_incorrect_old_password_when_updating_password_should_raise_invalid_credentials(
    use_case: UpdateUserPasswordUseCase,
    user_password_repository: FakeUserPasswordRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    actual_password = "ActualPassword123!"
    wrong_old_password = "WrongPassword123!"
    new_password = "NewPassword456!"

    # Create existing user with hashed password
    user_password = UserPassword(
        id=user_id,
        email="user@example.com",
        password_hash=password_hashing_gateway.hash(actual_password),
        display_name="Test User",
    )
    user_password_repository.save(user_password)

    command = UpdateUserPasswordCommand(
        user_id=user_id,
        old_password=wrong_old_password,
        new_password=new_password,
    )

    # Act & Assert
    with pytest.raises(InvalidCredentialsException):
        use_case.execute(command)


def test_given_user_not_in_password_repository_when_updating_password_should_raise_user_not_found(
    use_case: UpdateUserPasswordUseCase,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")

    command = UpdateUserPasswordCommand(
        user_id=user_id,
        old_password="OldPassword123!",
        new_password="NewPassword456!",
    )

    # Act & Assert
    with pytest.raises(UserNotFoundException):
        use_case.execute(command)


def test_given_valid_password_change_when_executing_should_publish_and_persist_event(
    use_case: UpdateUserPasswordUseCase,
    user_password_repository: FakeUserPasswordRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
    domain_event_publisher: FakeDomainEventPublisher,
    user_event_repository: FakeUserEventRepository,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    old_password = "OldPassword123!"
    new_password = "NewPassword456!"

    user_password = UserPassword(
        id=user_id,
        email="user@example.com",
        password_hash=password_hashing_gateway.hash(old_password),
        display_name="Test User",
    )
    user_password_repository.save(user_password)

    command = UpdateUserPasswordCommand(
        user_id=user_id,
        old_password=old_password,
        new_password=new_password,
    )

    # Act
    use_case.execute(command)

    # Assert event published
    assert len(domain_event_publisher.published_events) == 1
    event = domain_event_publisher.published_events[0]
    assert isinstance(event, UserPasswordChangedEvent)
    assert event.user_id == user_id

    # Assert event persisted
    assert len(user_event_repository.events) == 1
    persisted = user_event_repository.events[0]
    assert persisted["event_type"] == "UserPasswordChangedEvent"
    assert persisted["actor_user_id"] == user_id
    assert persisted["event_data"] == {"user_id": str(user_id)}
