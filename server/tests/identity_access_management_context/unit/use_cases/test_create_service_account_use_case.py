import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from identity_access_management_context.application.commands import CreateServiceAccountCommand
from identity_access_management_context.application.use_cases import CreateServiceAccountUseCase
from identity_access_management_context.domain.entities import Group, PersonalGroup
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    InvalidServiceAccountNameError,
    TooManyActiveServiceAccountsError,
    UserNotOwnerOfGroupException,
)
from shared_kernel.domain.entities import AuthenticatedUser

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
GROUP_ID = UUID("00000000-0000-0000-0000-0000000000b1")
OTHER_GROUP_ID = UUID("00000000-0000-0000-0000-0000000000b2")
OWNER_ID = UUID("00000000-0000-0000-0000-0000000000a1")
MEMBER_ID = UUID("00000000-0000-0000-0000-0000000000a2")
ADMIN_ID = UUID("00000000-0000-0000-0000-0000000000a3")

MAX_ACTIVE = 3


@pytest.fixture
def owner():
    return AuthenticatedUser(user_id=OWNER_ID, roles=[])


@pytest.fixture
def member():
    return AuthenticatedUser(user_id=MEMBER_ID, roles=[])


@pytest.fixture
def admin():
    return AuthenticatedUser(user_id=ADMIN_ID, roles=["admin"])


@pytest.fixture
def groups(group_repository, group_member_repository):
    group_repository.save_group(Group(id=GROUP_ID, name="Team", is_personal=False))
    group_repository.save_group(Group(id=OTHER_GROUP_ID, name="Other", is_personal=False))
    group_member_repository.add_member(GROUP_ID, OWNER_ID, is_owner=True)
    group_member_repository.add_member(GROUP_ID, MEMBER_ID, is_owner=False)
    group_member_repository.add_member(OTHER_GROUP_ID, OWNER_ID, is_owner=True)
    return group_repository


@pytest.fixture
def use_case(
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


def _create(use_case, user, name="nightly-backup", group_id=GROUP_ID):
    return use_case.execute(CreateServiceAccountCommand(requesting_user=user, group_id=group_id, name=name))


def test_given_an_owner_when_creating_then_returns_a_token_and_stores_only_its_hash(
    use_case, owner, groups, service_account_repository
):
    response = _create(use_case, owner)

    stored = list(service_account_repository.list_for_groups((GROUP_ID,)))
    assert len(stored) == 1
    assert stored[0].token_hash == hashlib.sha256(response.token.encode()).hexdigest()
    assert response.token not in [account.token_hash for account in stored]
    assert stored[0].is_active


def test_given_an_owner_of_a_personal_group_when_creating_then_it_succeeds(
    use_case, owner, group_repository, group_member_repository
):
    personal_id = uuid4()
    group_repository.save_personal_group(PersonalGroup(id=personal_id, name="Owner's Personal Group", user_id=OWNER_ID))
    group_member_repository.add_member(personal_id, OWNER_ID, is_owner=True)

    response = _create(use_case, owner, group_id=personal_id)

    assert response.group_id == personal_id


def test_given_a_plain_member_when_creating_then_it_is_refused(use_case, member, groups):
    with pytest.raises(UserNotOwnerOfGroupException):
        _create(use_case, member)


def test_given_an_admin_who_is_not_an_owner_when_creating_then_it_succeeds(use_case, admin, groups):
    assert _create(use_case, admin).group_id == GROUP_ID


def test_given_an_unknown_group_when_creating_then_it_is_refused(use_case, owner, groups):
    with pytest.raises(GroupNotFoundException):
        _create(use_case, owner, group_id=uuid4())


def test_given_the_cap_is_reached_when_creating_then_it_is_refused(use_case, owner, groups):
    for index in range(MAX_ACTIVE):
        _create(use_case, owner, name=f"account-{index}")

    with pytest.raises(TooManyActiveServiceAccountsError) as excinfo:
        _create(use_case, owner, name="one-too-many")

    assert excinfo.value.active_count == MAX_ACTIVE
    assert excinfo.value.max_active == MAX_ACTIVE


def test_given_the_cap_is_reached_when_one_is_revoked_then_a_slot_is_freed(
    use_case, owner, groups, service_account_repository
):
    for index in range(MAX_ACTIVE):
        _create(use_case, owner, name=f"account-{index}")
    first = next(iter(service_account_repository.accounts.values()))
    service_account_repository.revoke([first.id], NOW)

    assert _create(use_case, owner, name="replacement").name == "replacement"


@pytest.mark.parametrize("name", ["", "   ", "n" * 101])
def test_given_an_unusable_name_when_creating_then_it_is_refused(use_case, owner, groups, name):
    with pytest.raises(InvalidServiceAccountNameError):
        _create(use_case, owner, name=name)


def test_given_a_padded_name_when_creating_then_it_is_stored_stripped(use_case, owner, groups):
    assert _create(use_case, owner, name="  padded  ").name == "padded"


def test_given_a_creation_when_it_succeeds_then_it_is_audited_without_the_token(
    use_case, owner, groups, service_account_event_repository
):
    response = _create(use_case, owner)

    assert len(service_account_event_repository.events) == 1
    event = service_account_event_repository.events[0]
    assert event["event_type"] == "ServiceAccountCreatedEvent"
    assert event["actor_user_id"] == OWNER_ID
    assert event["occurred_on"] == NOW

    payload = json.dumps(event["event_data"])
    assert response.token not in payload
    assert hashlib.sha256(response.token.encode()).hexdigest() not in payload
