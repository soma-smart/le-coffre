from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from identity_access_management_context.application.commands import (
    CreateServiceAccountCommand,
    ListServiceAccountsCommand,
)
from identity_access_management_context.application.use_cases import (
    CreateServiceAccountUseCase,
    ListServiceAccountsUseCase,
)
from identity_access_management_context.domain.entities import Group, ServiceAccount, User
from identity_access_management_context.domain.exceptions import UserNotOwnerOfGroupException
from identity_access_management_context.domain.value_objects import ServiceAccountToken
from shared_kernel.domain.entities import AuthenticatedUser

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 2, 1, 12, 0, 0, tzinfo=UTC)
GROUP_ID = UUID("00000000-0000-0000-0000-0000000000b1")
OWNER_ID = UUID("00000000-0000-0000-0000-0000000000a1")
MEMBER_ID = UUID("00000000-0000-0000-0000-0000000000a2")

MAX_ACTIVE = 3


@pytest.fixture
def owner():
    return AuthenticatedUser(user_id=OWNER_ID, roles=[])


@pytest.fixture
def groups(group_repository, group_member_repository, user_repository):
    group_repository.save_group(Group(id=GROUP_ID, name="Team", is_personal=False))
    group_member_repository.add_member(GROUP_ID, OWNER_ID, is_owner=True)
    group_member_repository.add_member(GROUP_ID, MEMBER_ID, is_owner=False)
    user_repository.save(User(id=OWNER_ID, username="owner", email="owner@example.com", name="Ada Owner"))


@pytest.fixture
def create_use_case(
    service_account_repository,
    group_management_permission_service,
    event_publisher,
    service_account_event_repository,
    time_provider,
):
    time_provider.set_current_time(NOW)
    return CreateServiceAccountUseCase(
        service_account_repository,
        group_management_permission_service,
        event_publisher,
        service_account_event_repository,
        time_provider,
        max_active_accounts=MAX_ACTIVE,
    )


@pytest.fixture
def use_case(
    service_account_repository,
    group_management_permission_service,
    event_publisher,
    service_account_event_repository,
    time_provider,
    user_repository,
):
    return ListServiceAccountsUseCase(
        service_account_repository,
        group_management_permission_service,
        event_publisher,
        service_account_event_repository,
        time_provider,
        user_repository,
    )


def _list(use_case, user):
    return use_case.execute(ListServiceAccountsCommand(requesting_user=user, group_id=GROUP_ID))


def test_given_an_account_when_listing_then_the_creation_facts_come_from_the_event(
    create_use_case, use_case, owner, groups
):
    create_use_case.execute(CreateServiceAccountCommand(requesting_user=owner, group_id=GROUP_ID, name="nightly"))

    summary = _list(use_case, owner).items[0]

    assert summary.name == "nightly"
    assert summary.created_at == NOW
    assert summary.created_by_user_id == OWNER_ID
    assert summary.created_by_user_name == "Ada Owner"
    assert summary.revoked_at is None


def test_given_a_revoked_account_when_listing_then_it_appears_with_its_status(
    create_use_case, use_case, owner, groups, service_account_repository
):
    created = create_use_case.execute(
        CreateServiceAccountCommand(requesting_user=owner, group_id=GROUP_ID, name="nightly")
    )
    service_account_repository.revoke([created.id], LATER)

    summary = _list(use_case, owner).items[0]

    assert summary.revoked_at == LATER


def test_given_an_account_with_no_creation_event_when_listing_then_it_still_appears(
    use_case, owner, groups, service_account_repository
):
    orphan = ServiceAccount.create(group_id=GROUP_ID, name="orphan", token=ServiceAccountToken.generate())
    service_account_repository.create([orphan])

    summary = _list(use_case, owner).items[0]

    assert summary.name == "orphan"
    assert summary.created_at is None
    assert summary.created_by_user_id is None
    assert summary.created_by_user_name is None


def test_given_a_deleted_creator_when_listing_then_the_display_name_is_empty(
    create_use_case, use_case, owner, groups, user_repository
):
    create_use_case.execute(CreateServiceAccountCommand(requesting_user=owner, group_id=GROUP_ID, name="nightly"))
    user_repository.delete(OWNER_ID)

    summary = _list(use_case, owner).items[0]

    assert summary.created_by_user_id == OWNER_ID
    assert summary.created_by_user_name is None


def test_given_accounts_with_and_without_creation_events_when_listing_then_undated_sort_last(
    create_use_case, use_case, owner, groups, service_account_repository
):
    create_use_case.execute(CreateServiceAccountCommand(requesting_user=owner, group_id=GROUP_ID, name="dated"))
    for name in ("orphan-one", "orphan-two"):
        service_account_repository.create(
            [ServiceAccount.create(group_id=GROUP_ID, name=name, token=ServiceAccountToken.generate())]
        )

    names = [summary.name for summary in _list(use_case, owner).items]

    assert names[0] == "dated"
    assert set(names[1:]) == {"orphan-one", "orphan-two"}


def test_given_a_plain_member_when_listing_then_it_is_refused(use_case, groups):
    with pytest.raises(UserNotOwnerOfGroupException):
        _list(use_case, AuthenticatedUser(user_id=MEMBER_ID, roles=[]))


def test_given_another_groups_account_when_listing_then_it_is_not_included(
    use_case, owner, groups, service_account_repository
):
    service_account_repository.create(
        [ServiceAccount.create(group_id=uuid4(), name="elsewhere", token=ServiceAccountToken.generate())]
    )

    assert _list(use_case, owner).items == ()
