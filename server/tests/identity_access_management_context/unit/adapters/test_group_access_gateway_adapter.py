from datetime import UTC, datetime
from uuid import uuid4

import pytest

from identity_access_management_context.adapters.secondary.group_access_gateway_adapter import (
    GroupAccessGatewayAdapter,
)
from identity_access_management_context.domain.entities import Group, PersonalGroup, ServiceAccount

from ..fakes import FakeGroupMemberRepository, FakeGroupRepository, FakeServiceAccountRepository


@pytest.fixture
def adapter(
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    service_account_repository: FakeServiceAccountRepository,
):
    return GroupAccessGatewayAdapter(group_repository, group_member_repository, service_account_repository)


def test_should_return_true_when_user_owns_group(
    adapter: GroupAccessGatewayAdapter,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    user_id = uuid4()
    group_id = uuid4()
    group = Group(id=group_id, name="Test Group", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, user_id, is_owner=True)

    result = adapter.is_principal_owner_of_group(user_id, group_id)

    assert result is True


def test_should_return_false_when_user_does_not_own_group(adapter, group_repository: FakeGroupRepository):
    user_id = uuid4()
    other_user_id = uuid4()
    group_id = uuid4()
    group = PersonalGroup(id=group_id, name="Test Group", principal_id=other_user_id)
    group_repository.save_personal_group(group)

    result = adapter.is_principal_owner_of_group(user_id, group_id)

    assert result is False


def test_should_return_false_when_group_does_not_exist(adapter):
    user_id = uuid4()
    nonexistent_group_id = uuid4()

    result = adapter.is_principal_owner_of_group(user_id, nonexistent_group_id)

    assert result is False


def test_should_return_true_when_group_exists(
    adapter,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    user_id = uuid4()
    group_id = uuid4()
    group = Group(id=group_id, name="Test Group", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, user_id, is_owner=True)

    result = adapter.group_exists(group_id)

    assert result is True


def test_should_return_false_when_group_does_not_exist_for_exists_check(adapter):
    nonexistent_group_id = uuid4()

    result = adapter.group_exists(nonexistent_group_id)

    assert result is False


def test_should_return_only_owners_when_getting_group_owner_users(
    adapter: GroupAccessGatewayAdapter,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = uuid4()
    member_id = uuid4()
    group_id = uuid4()
    group_repository.save_group(Group(id=group_id, name="Test Group", is_personal=False))
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, member_id, is_owner=False)

    result = adapter.get_group_owner_principals(group_id)

    assert result == [owner_id]


def test_should_return_only_non_owner_members_when_getting_group_member_users(
    adapter: GroupAccessGatewayAdapter,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = uuid4()
    member_id = uuid4()
    group_id = uuid4()
    group_repository.save_group(Group(id=group_id, name="Test Group", is_personal=False))
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, member_id, is_owner=False)

    result = adapter.get_group_member_principals(group_id)

    assert result == [member_id]


def test_should_return_empty_member_list_for_personal_group(
    adapter: GroupAccessGatewayAdapter,
    group_repository: FakeGroupRepository,
):
    user_id = uuid4()
    group_id = uuid4()
    group_repository.save_personal_group(PersonalGroup(id=group_id, name="Personal", principal_id=user_id))

    assert adapter.get_group_member_principals(group_id) == []


# ── Service accounts ─────────────────────────────────────────────────


@pytest.fixture
def shared_group(group_repository: FakeGroupRepository) -> Group:
    group = Group(id=uuid4(), name="Deployments", is_personal=False)
    group_repository.save_group(group)
    return group


def test_given_an_active_service_account_when_checking_its_group_then_it_is_a_member_but_not_an_owner(
    adapter, shared_group, service_account_repository: FakeServiceAccountRepository
):
    account = ServiceAccount.create(group_id=shared_group.id, name="nightly-backup")
    service_account_repository.create([account])

    assert adapter.is_principal_member_of_group(account.id, shared_group.id) is True
    assert adapter.is_principal_owner_of_group(account.id, shared_group.id) is False


def test_given_a_service_account_when_checking_another_group_then_it_is_not_a_member(
    adapter, shared_group, group_repository: FakeGroupRepository, service_account_repository
):
    other_group = Group(id=uuid4(), name="Other", is_personal=False)
    group_repository.save_group(other_group)
    account = ServiceAccount.create(group_id=shared_group.id, name="nightly-backup")
    service_account_repository.create([account])

    assert adapter.is_principal_member_of_group(account.id, other_group.id) is False


def test_given_a_revoked_service_account_when_checking_its_group_then_it_is_no_longer_a_member(
    adapter, shared_group, service_account_repository: FakeServiceAccountRepository
):
    account = ServiceAccount.create(group_id=shared_group.id, name="nightly-backup")
    service_account_repository.create([account])
    service_account_repository.revoke([account.id], datetime.now(UTC))

    assert adapter.is_principal_member_of_group(account.id, shared_group.id) is False


def test_given_a_service_account_of_a_personal_group_when_checking_it_then_it_is_a_member_not_the_owner(
    adapter, group_repository: FakeGroupRepository, service_account_repository
):
    owner_id = uuid4()
    personal = Group(id=uuid4(), name="Alice", is_personal=True, principal_id=owner_id)
    group_repository.save_group(personal)
    account = ServiceAccount.create(group_id=personal.id, name="laptop-sync")
    service_account_repository.create([account])

    assert adapter.is_principal_member_of_group(account.id, personal.id) is True
    assert adapter.is_principal_owner_of_group(account.id, personal.id) is False
    assert adapter.get_group_member_principals(personal.id) == []


def test_given_a_service_account_when_listing_group_principals_then_it_is_not_among_them(
    adapter, shared_group, service_account_repository
):
    """Membership lists drive notifications and the members UI: a machine has no place there."""
    account = ServiceAccount.create(group_id=shared_group.id, name="nightly-backup")
    service_account_repository.create([account])

    assert account.id not in adapter.get_group_member_principals(shared_group.id)
    assert account.id not in adapter.get_group_owner_principals(shared_group.id)
