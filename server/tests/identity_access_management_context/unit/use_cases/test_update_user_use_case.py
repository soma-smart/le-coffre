from uuid import UUID, uuid4

import pytest

from identity_access_management_context.application.commands import UpdateUserCommand
from identity_access_management_context.application.use_cases import UpdateUserUseCase
from identity_access_management_context.domain.entities import PasswordCredentialRecord, User
from identity_access_management_context.domain.events import UserUpdatedEvent
from identity_access_management_context.domain.exceptions import (
    EmailAlreadyUsedException,
    UserUpdateNotAllowedException,
)
from shared_kernel.domain.entities import AuthenticatedUser
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher

from ..fakes import FakePasswordCredentialRecordRepository, FakeUserRepository


@pytest.fixture
def use_case(
    user_repository: FakeUserRepository,
    password_credential_record_repository: FakePasswordCredentialRecordRepository,
    event_publisher,
    user_event_repository,
):
    return UpdateUserUseCase(
        user_repository, password_credential_record_repository, event_publisher, user_event_repository
    )


def test_given_user_updating_own_profile_when_updating_should_persist_changes(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "User"

    user = User(id=uuid, username=username, email=email, name=name)
    user_repository.save(user)

    new_username = "updateduser"
    new_email = "updateduser@example.com"
    new_name = "New User"

    command = UpdateUserCommand(
        requesting_user=AuthenticatedUser(user_id=uuid, roles=[]),
        id=uuid,
        username=new_username,
        email=new_email,
        name=new_name,
    )

    use_case.execute(command)
    updated_user = user_repository.get_by_id(uuid)
    assert updated_user is not None
    assert updated_user.id == uuid
    assert updated_user.username == new_username
    assert updated_user.email == new_email
    assert updated_user.name == new_name


def test_given_admin_updating_another_user_when_updating_should_persist_changes(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
):
    target_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_uuid = UUID("123e4567-e89b-12d3-a456-426614174001")

    user = User(id=target_uuid, username="testuser", email="testuser@example.com", name="User")
    user_repository.save(user)

    command = UpdateUserCommand(
        requesting_user=AuthenticatedUser(user_id=admin_uuid, roles=["admin"]),
        id=target_uuid,
        username="updateduser",
        email="updateduser@example.com",
        name="New User",
    )

    use_case.execute(command)

    updated_user = user_repository.get_by_id(target_uuid)
    assert updated_user is not None
    assert updated_user.username == "updateduser"
    assert updated_user.email == "updateduser@example.com"
    assert updated_user.name == "New User"


def test_given_non_admin_updating_another_user_when_updating_should_raise_user_update_not_allowed(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
):
    target_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    other_uuid = UUID("123e4567-e89b-12d3-a456-426614174002")

    user = User(id=target_uuid, username="testuser", email="testuser@example.com", name="User")
    user_repository.save(user)

    command = UpdateUserCommand(
        requesting_user=AuthenticatedUser(user_id=other_uuid, roles=[]),
        id=target_uuid,
        username="hacked",
        email="hacked@example.com",
        name="Hacked",
    )

    with pytest.raises(UserUpdateNotAllowedException):
        use_case.execute(command)

    unchanged_user = user_repository.get_by_id(target_uuid)
    assert unchanged_user is not None
    assert unchanged_user.username == "testuser"
    assert unchanged_user.email == "testuser@example.com"
    assert unchanged_user.name == "User"


def test_given_user_updating_own_profile_when_updating_should_publish_user_updated_event(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    event_publisher: FakeDomainEventPublisher,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    user = User(id=uuid, username="testuser", email="testuser@example.com", name="User")
    user_repository.save(user)

    command = UpdateUserCommand(
        requesting_user=AuthenticatedUser(user_id=uuid, roles=[]),
        id=uuid,
        username="updateduser",
        email="updateduser@example.com",
        name="New User",
    )

    use_case.execute(command)

    events = event_publisher.get_published_events_of_type(UserUpdatedEvent)
    assert len(events) == 1
    assert events[0].user_id == uuid
    assert events[0].updated_by_principal_id == uuid


def test_given_admin_updating_another_user_when_updating_should_record_admin_as_actor(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    event_publisher: FakeDomainEventPublisher,
    user_event_repository,
):
    target_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_uuid = UUID("123e4567-e89b-12d3-a456-426614174001")

    user = User(id=target_uuid, username="testuser", email="testuser@example.com", name="User")
    user_repository.save(user)

    command = UpdateUserCommand(
        requesting_user=AuthenticatedUser(user_id=admin_uuid, roles=["admin"]),
        id=target_uuid,
        username="updateduser",
        email="updateduser@example.com",
        name="New User",
    )

    use_case.execute(command)

    events = event_publisher.get_published_events_of_type(UserUpdatedEvent)
    assert len(events) == 1
    assert events[0].user_id == target_uuid
    assert events[0].updated_by_principal_id == admin_uuid

    assert len(user_event_repository.events) == 1
    assert user_event_repository.events[0]["actor_principal_id"] == admin_uuid


def test_given_user_updating_own_profile_when_updating_should_store_user_updated_event(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    user_event_repository,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    user = User(id=uuid, username="testuser", email="testuser@example.com", name="User")
    user_repository.save(user)

    command = UpdateUserCommand(
        requesting_user=AuthenticatedUser(user_id=uuid, roles=[]),
        id=uuid,
        username="updateduser",
        email="updateduser@example.com",
        name="New User",
    )

    use_case.execute(command)

    assert len(user_event_repository.events) == 1
    stored = user_event_repository.events[0]
    assert stored["event_type"] == "UserUpdatedEvent"
    assert stored["actor_principal_id"] == uuid


def test_given_an_email_of_another_user_when_updating_should_refuse_it(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
):
    alice, bob = uuid4(), uuid4()
    user_repository.save(User(id=alice, username="alice", email="alice@example.com", name="Alice"))
    user_repository.save(User(id=bob, username="bob", email="bob@example.com", name="Bob"))

    with pytest.raises(EmailAlreadyUsedException):
        use_case.execute(
            UpdateUserCommand(
                requesting_user=AuthenticatedUser(user_id=alice, roles=[]),
                id=alice,
                username="alice",
                email="bob@example.com",
                name="Alice",
            )
        )

    assert user_repository.get_by_id(alice).email == "alice@example.com"


def test_given_an_unchanged_email_when_updating_should_accept_it(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
):
    alice = uuid4()
    user_repository.save(User(id=alice, username="alice", email="alice@example.com", name="Alice"))

    use_case.execute(
        UpdateUserCommand(
            requesting_user=AuthenticatedUser(user_id=alice, roles=[]),
            id=alice,
            username="alice",
            email="alice@example.com",
            name="Alice Liddell",
        )
    )

    assert user_repository.get_by_id(alice).name == "Alice Liddell"


def _alice_with_password(user_repository, password_credential_record_repository, email="alice@old.fr") -> UUID:
    alice = uuid4()
    user_repository.save(User(id=alice, username="alice", email=email, name="Alice"))
    password_credential_record_repository.save(
        PasswordCredentialRecord(principal_id=alice, email=email, password_hash=b"alice-hash")
    )
    return alice


def _change_email(use_case, user_id: UUID, email: str, requesting_user_id: UUID | None = None, roles=()):
    use_case.execute(
        UpdateUserCommand(
            requesting_user=AuthenticatedUser(user_id=requesting_user_id or user_id, roles=list(roles)),
            id=user_id,
            username="alice",
            email=email,
            name="Alice",
        )
    )


def test_given_a_password_user_when_an_admin_changes_its_email_then_the_login_follows(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    password_credential_record_repository: FakePasswordCredentialRecordRepository,
):
    alice = _alice_with_password(user_repository, password_credential_record_repository)

    _change_email(use_case, alice, "alice@new.fr", requesting_user_id=uuid4(), roles=["admin"])

    assert user_repository.get_by_id(alice).email == "alice@new.fr"
    assert password_credential_record_repository.get_by_email("alice@new.fr").principal_id == alice
    assert password_credential_record_repository.get_by_email("alice@old.fr") is None


def test_given_a_password_user_when_changing_its_email_then_the_password_is_kept(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    password_credential_record_repository: FakePasswordCredentialRecordRepository,
):
    alice = _alice_with_password(user_repository, password_credential_record_repository)

    _change_email(use_case, alice, "alice@new.fr")

    assert password_credential_record_repository.get_by_email("alice@new.fr").password_hash == b"alice-hash"


def test_given_a_second_password_login_when_changing_the_email_then_only_the_mirrored_one_follows(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    password_credential_record_repository: FakePasswordCredentialRecordRepository,
):
    alice = _alice_with_password(user_repository, password_credential_record_repository)
    password_credential_record_repository.save(
        PasswordCredentialRecord(principal_id=alice, email="alice@home.fr", password_hash=b"home-hash")
    )

    _change_email(use_case, alice, "alice@new.fr")

    emails = {c.email for c in password_credential_record_repository.list_by_principal_id(alice)}
    assert emails == {"alice@new.fr", "alice@home.fr"}


def test_given_an_email_another_account_logs_in_with_when_updating_then_it_is_refused(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    password_credential_record_repository: FakePasswordCredentialRecordRepository,
):
    """A login email the app no longer shows (data diverged before this fix) is still taken."""
    alice = _alice_with_password(user_repository, password_credential_record_repository)
    bob = uuid4()
    user_repository.save(User(id=bob, username="bob", email="bob@new.fr", name="Bob"))
    password_credential_record_repository.save(
        PasswordCredentialRecord(principal_id=bob, email="bob@old.fr", password_hash=b"bob-hash")
    )

    with pytest.raises(EmailAlreadyUsedException):
        _change_email(use_case, alice, "bob@old.fr")

    assert user_repository.get_by_id(alice).email == "alice@old.fr"
    assert password_credential_record_repository.get_by_email("alice@old.fr").principal_id == alice


def test_given_a_login_owned_by_someone_else_when_changing_the_email_then_it_is_left_alone(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    password_credential_record_repository: FakePasswordCredentialRecordRepository,
):
    """Bob shows an address that is still Alice's login: changing Bob must not move Alice's login."""
    alice = uuid4()
    user_repository.save(User(id=alice, username="alice", email="alice@new.fr", name="Alice"))
    password_credential_record_repository.save(
        PasswordCredentialRecord(principal_id=alice, email="shared@old.fr", password_hash=b"alice-hash")
    )
    bob = uuid4()
    user_repository.save(User(id=bob, username="bob", email="shared@old.fr", name="Bob"))

    _change_email(use_case, bob, "bob@new.fr")

    assert password_credential_record_repository.get_by_email("shared@old.fr").principal_id == alice


def test_given_an_sso_user_without_password_when_changing_its_email_then_it_is_saved(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    password_credential_record_repository: FakePasswordCredentialRecordRepository,
):
    alice = uuid4()
    user_repository.save(User(id=alice, username="alice", email="alice@old.fr", name="Alice"))

    _change_email(use_case, alice, "alice@new.fr")

    assert user_repository.get_by_id(alice).email == "alice@new.fr"
    assert password_credential_record_repository.list_by_principal_id(alice) == []


def test_given_the_user_cannot_be_saved_when_changing_its_email_then_the_login_is_restored(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    password_credential_record_repository: FakePasswordCredentialRecordRepository,
    monkeypatch,
):
    alice = _alice_with_password(user_repository, password_credential_record_repository)

    def fail(user):
        raise RuntimeError("connection lost")

    monkeypatch.setattr(user_repository, "update", fail)
    with pytest.raises(RuntimeError):
        _change_email(use_case, alice, "alice@new.fr")

    assert password_credential_record_repository.get_by_email("alice@old.fr").principal_id == alice
    assert password_credential_record_repository.get_by_email("alice@new.fr") is None


def test_given_the_user_already_logs_in_with_the_new_email_when_switching_to_it_then_both_logins_are_kept(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    password_credential_record_repository: FakePasswordCredentialRecordRepository,
):
    alice = _alice_with_password(user_repository, password_credential_record_repository)
    password_credential_record_repository.save(
        PasswordCredentialRecord(principal_id=alice, email="alice@home.fr", password_hash=b"home-hash")
    )

    _change_email(use_case, alice, "alice@home.fr")

    assert user_repository.get_by_id(alice).email == "alice@home.fr"
    emails = {c.email for c in password_credential_record_repository.list_by_principal_id(alice)}
    assert emails == {"alice@old.fr", "alice@home.fr"}
