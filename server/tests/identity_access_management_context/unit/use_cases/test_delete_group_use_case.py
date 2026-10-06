from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from identity_access_management_context.application.commands import DeleteGroupCommand
from identity_access_management_context.application.gateways import (
    GroupMemberRepository,
    GroupRepository,
    GroupUsageGateway,
)
from identity_access_management_context.application.use_cases import DeleteGroupUseCase
from identity_access_management_context.domain.entities import Group, ServiceAccount
from identity_access_management_context.domain.events import GroupDeletedEvent
from identity_access_management_context.domain.exceptions import (
    CannotDeleteGroupStillUsedException,
    CannotDeletePersonalGroupException,
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
)
from identity_access_management_context.domain.value_objects import ServiceAccountToken
from shared_kernel.domain.entities import AuthenticatedUser
from shared_kernel.domain.value_objects import ADMIN_ROLE
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def use_case(
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
    group_usage_gateway: GroupUsageGateway,
    event_publisher,
    group_event_repository,
    service_account_repository,
    service_account_event_repository,
    time_provider,
):
    time_provider.set_current_time(NOW)
    return DeleteGroupUseCase(
        group_repository=group_repository,
        group_member_repository=group_member_repository,
        group_usage_gateway=group_usage_gateway,
        event_publisher=event_publisher,
        group_event_repository=group_event_repository,
        service_account_repository=service_account_repository,
        service_account_event_repository=service_account_event_repository,
        time_provider=time_provider,
    )


def test_given_owner_and_group_without_passwords_when_deleting_group_then_group_is_deleted(
    use_case: DeleteGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    # Arrange
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    group = Group(
        id=group_id,
        name="Test Group",
        is_personal=False,
    )
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    requesting_user = AuthenticatedUser(user_id=owner_id, roles=[])
    command = DeleteGroupCommand(
        requesting_user=requesting_user,
        group_id=group_id,
    )

    # Act
    use_case.execute(command)

    # Assert
    assert group_repository.get_by_id(group_id) is None


def test_given_non_owner_user_when_deleting_group_then_raises_user_not_owner_exception(
    use_case: DeleteGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    # Arrange
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    non_owner_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    group_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    group = Group(
        id=group_id,
        name="Test Group",
        is_personal=False,
    )
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, non_owner_id, is_owner=False)

    requesting_user = AuthenticatedUser(user_id=non_owner_id, roles=[])
    command = DeleteGroupCommand(
        requesting_user=requesting_user,
        group_id=group_id,
    )

    # Act & Assert
    with pytest.raises(UserNotOwnerOfGroupException):
        use_case.execute(command)


def test_given_non_existent_group_when_deleting_group_then_raises_group_not_found_exception(
    use_case: DeleteGroupUseCase,
):
    # Arrange
    requester_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    non_existent_group_id = UUID("999e4567-e89b-12d3-a456-426614174999")

    requesting_user = AuthenticatedUser(user_id=requester_id, roles=[])
    command = DeleteGroupCommand(
        requesting_user=requesting_user,
        group_id=non_existent_group_id,
    )

    # Act & Assert
    with pytest.raises(GroupNotFoundException):
        use_case.execute(command)


def test_given_personal_group_when_deleting_group_then_raises_cannot_delete_personal_group_exception(
    use_case: DeleteGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    # Arrange
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    personal_group_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    personal_group = Group(
        id=personal_group_id,
        name="Personal Group",
        is_personal=True,
        user_id=user_id,
    )
    group_repository.save_group(personal_group)
    group_member_repository.add_member(personal_group_id, user_id, is_owner=True)

    requesting_user = AuthenticatedUser(user_id=user_id, roles=[])
    command = DeleteGroupCommand(
        requesting_user=requesting_user,
        group_id=personal_group_id,
    )

    # Act & Assert
    with pytest.raises(CannotDeletePersonalGroupException):
        use_case.execute(command)


def test_given_group_with_passwords_when_deleting_group_then_raises_cannot_delete_group_with_passwords_exception(
    use_case: DeleteGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
    group_usage_gateway: GroupUsageGateway,
):
    # Arrange
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    group = Group(
        id=group_id,
        name="Test Group",
        is_personal=False,
    )
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    # Simulate that this group owns passwords
    group_usage_gateway._set_usage_to_group(group_id)

    requesting_user = AuthenticatedUser(user_id=owner_id, roles=[])
    command = DeleteGroupCommand(
        requesting_user=requesting_user,
        group_id=group_id,
    )

    # Act & Assert
    with pytest.raises(CannotDeleteGroupStillUsedException):
        use_case.execute(command)


def test_given_admin_user_not_owner_when_deleting_group_then_group_is_deleted(
    use_case: DeleteGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    # Arrange
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    group_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    group = Group(
        id=group_id,
        name="Test Group",
        is_personal=False,
    )
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    # Admin is not a member of the group

    requesting_user = AuthenticatedUser(user_id=admin_id, roles=[ADMIN_ROLE])
    command = DeleteGroupCommand(
        requesting_user=requesting_user,
        group_id=group_id,
    )

    # Act
    use_case.execute(command)

    # Assert
    assert group_repository.get_by_id(group_id) is None


def test_given_owner_when_deleting_group_then_should_publish_group_deleted_event(
    use_case: DeleteGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
    event_publisher: FakeDomainEventPublisher,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    group = Group(id=group_id, name="Test Group", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    requesting_user = AuthenticatedUser(user_id=owner_id, roles=[])
    command = DeleteGroupCommand(requesting_user=requesting_user, group_id=group_id)

    use_case.execute(command)

    events = event_publisher.get_published_events_of_type(GroupDeletedEvent)
    assert len(events) == 1
    assert events[0].group_id == group_id
    assert events[0].deleted_by_user_id == owner_id


def test_given_owner_when_deleting_group_then_should_store_group_deleted_event(
    use_case: DeleteGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
    group_event_repository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    group = Group(id=group_id, name="Test Group", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    requesting_user = AuthenticatedUser(user_id=owner_id, roles=[])
    command = DeleteGroupCommand(requesting_user=requesting_user, group_id=group_id)

    use_case.execute(command)

    assert len(group_event_repository.events) == 1
    stored = group_event_repository.events[0]
    assert stored["event_type"] == "GroupDeletedEvent"
    assert stored["actor_user_id"] == owner_id


def _service_account(group_id, name="nightly-backup"):
    return ServiceAccount.create(group_id=group_id, name=name, token=ServiceAccountToken.generate())


def test_given_a_group_with_service_accounts_when_deleting_then_they_are_revoked(
    use_case, group_repository, group_member_repository, service_account_repository
):
    group_id = uuid4()
    owner_id = uuid4()
    group_repository.save_group(Group(id=group_id, name="Team", is_personal=False))
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    accounts = [_service_account(group_id, "a"), _service_account(group_id, "b")]
    service_account_repository.create(accounts)

    use_case.execute(DeleteGroupCommand(requesting_user=AuthenticatedUser(owner_id, []), group_id=group_id))

    assert all(not service_account_repository.accounts[a.id].is_active for a in accounts)
    assert all(service_account_repository.accounts[a.id].revoked_at == NOW for a in accounts)


def test_given_a_group_with_service_accounts_when_deleting_then_the_rows_survive_for_the_audit(
    use_case, group_repository, group_member_repository, service_account_repository
):
    group_id = uuid4()
    owner_id = uuid4()
    group_repository.save_group(Group(id=group_id, name="Team", is_personal=False))
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    account = _service_account(group_id)
    service_account_repository.create([account])

    use_case.execute(DeleteGroupCommand(requesting_user=AuthenticatedUser(owner_id, []), group_id=group_id))

    assert account.id in service_account_repository.accounts


def test_given_a_group_with_service_accounts_when_deleting_then_each_revocation_is_audited(
    use_case, group_repository, group_member_repository, service_account_repository, service_account_event_repository
):
    group_id = uuid4()
    owner_id = uuid4()
    group_repository.save_group(Group(id=group_id, name="Team", is_personal=False))
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    service_account_repository.create([_service_account(group_id, "a"), _service_account(group_id, "b")])

    use_case.execute(DeleteGroupCommand(requesting_user=AuthenticatedUser(owner_id, []), group_id=group_id))

    revocations = [
        e for e in service_account_event_repository.events if e["event_type"] == "ServiceAccountRevokedEvent"
    ]
    assert len(revocations) == 2
    assert all(e["actor_user_id"] == owner_id for e in revocations)


def test_given_an_already_revoked_service_account_when_deleting_the_group_then_it_is_left_alone(
    use_case, group_repository, group_member_repository, service_account_repository
):
    """Revoking it twice would raise, and would overwrite the original timestamp."""
    group_id = uuid4()
    owner_id = uuid4()
    earlier = datetime(2025, 6, 1, 9, 0, 0, tzinfo=UTC)
    group_repository.save_group(Group(id=group_id, name="Team", is_personal=False))
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    account = _service_account(group_id)
    service_account_repository.create([account])
    service_account_repository.revoke([account.id], earlier)

    use_case.execute(DeleteGroupCommand(requesting_user=AuthenticatedUser(owner_id, []), group_id=group_id))

    assert service_account_repository.accounts[account.id].revoked_at == earlier


def test_given_a_group_whose_only_attachment_is_service_accounts_when_deleting_then_it_is_deletable(
    use_case, group_repository, group_member_repository, service_account_repository
):
    """Service accounts are not group "usage": they are revoked, not a reason to refuse."""
    group_id = uuid4()
    owner_id = uuid4()
    group_repository.save_group(Group(id=group_id, name="Team", is_personal=False))
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    service_account_repository.create([_service_account(group_id)])

    use_case.execute(DeleteGroupCommand(requesting_user=AuthenticatedUser(owner_id, []), group_id=group_id))

    assert group_repository.get_by_id(group_id) is None


def test_given_another_groups_service_account_when_deleting_then_it_is_untouched(
    use_case, group_repository, group_member_repository, service_account_repository
):
    group_id, other_group_id = uuid4(), uuid4()
    owner_id = uuid4()
    group_repository.save_group(Group(id=group_id, name="Team", is_personal=False))
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    survivor = _service_account(other_group_id, "elsewhere")
    service_account_repository.create([_service_account(group_id), survivor])

    use_case.execute(DeleteGroupCommand(requesting_user=AuthenticatedUser(owner_id, []), group_id=group_id))

    assert service_account_repository.accounts[survivor.id].is_active
