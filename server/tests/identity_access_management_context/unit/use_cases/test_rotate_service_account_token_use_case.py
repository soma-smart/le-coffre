import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from identity_access_management_context.application.commands import (
    CreateServiceAccountCommand,
    RotateServiceAccountTokenCommand,
)
from identity_access_management_context.application.use_cases import (
    CreateServiceAccountUseCase,
    RotateServiceAccountTokenUseCase,
)
from identity_access_management_context.domain.entities import Group
from identity_access_management_context.domain.exceptions import (
    ServiceAccountAlreadyRevokedException,
    ServiceAccountNotFoundException,
    UserNotOwnerOfGroupException,
)
from shared_kernel.domain.entities import AuthenticatedUser

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 2, 1, 12, 0, 0, tzinfo=UTC)
GROUP_ID = UUID("00000000-0000-0000-0000-0000000000b1")
OWNER_ID = UUID("00000000-0000-0000-0000-0000000000a1")
MEMBER_ID = UUID("00000000-0000-0000-0000-0000000000a2")


@pytest.fixture
def owner():
    return AuthenticatedUser(user_id=OWNER_ID, roles=[])


@pytest.fixture
def groups(group_repository, group_member_repository):
    group_repository.save_group(Group(id=GROUP_ID, name="Team", is_personal=False))
    group_member_repository.add_member(GROUP_ID, OWNER_ID, is_owner=True)
    group_member_repository.add_member(GROUP_ID, MEMBER_ID, is_owner=False)


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
        max_active_accounts=3,
    )


@pytest.fixture
def use_case(
    service_account_repository,
    group_management_permission_service,
    event_publisher,
    service_account_event_repository,
    time_provider,
):
    return RotateServiceAccountTokenUseCase(
        service_account_repository,
        group_management_permission_service,
        event_publisher,
        service_account_event_repository,
        time_provider,
    )


@pytest.fixture
def account(create_use_case, owner, groups):
    return create_use_case.execute(
        CreateServiceAccountCommand(requesting_user=owner, group_id=GROUP_ID, name="nightly-backup")
    )


def _rotate(use_case, user, account_id):
    return use_case.execute(RotateServiceAccountTokenCommand(requesting_user=user, service_account_id=account_id))


def test_given_an_active_account_when_rotating_then_the_stored_hash_is_replaced(
    use_case, owner, account, service_account_repository, service_account_event_repository, time_provider
):
    time_provider.set_current_time(LATER)
    old_hash = service_account_repository.accounts[account.id].token_hash

    rotated = _rotate(use_case, owner, account.id)

    stored = service_account_repository.accounts[account.id]
    assert rotated.token != account.token
    assert stored.token_hash == hashlib.sha256(rotated.token.encode()).hexdigest()
    assert stored.token_hash != old_hash
    assert service_account_event_repository.events[-1]["occurred_on"] == LATER


def test_given_a_rotation_when_it_succeeds_then_the_account_keeps_its_identity(
    use_case, owner, account, service_account_repository
):
    before = service_account_repository.accounts[account.id]
    name, group_id = before.name, before.group_id

    _rotate(use_case, owner, account.id)

    after = service_account_repository.accounts[account.id]
    assert (after.id, after.name, after.group_id) == (account.id, name, group_id)


def test_given_a_rotation_when_it_succeeds_then_the_creation_facts_are_untouched(
    use_case, owner, account, service_account_event_repository
):
    before = service_account_event_repository.get_creation_facts([account.id])[0]

    _rotate(use_case, owner, account.id)

    after = service_account_event_repository.get_creation_facts([account.id])[0]
    assert after == before


def test_given_a_plain_member_when_rotating_then_it_is_refused(use_case, account, groups):
    with pytest.raises(UserNotOwnerOfGroupException):
        _rotate(use_case, AuthenticatedUser(user_id=MEMBER_ID, roles=[]), account.id)


def test_given_an_unknown_account_when_rotating_then_it_is_not_found(use_case, owner, groups):
    with pytest.raises(ServiceAccountNotFoundException):
        _rotate(use_case, owner, uuid4())


def test_given_a_revoked_account_when_rotating_then_it_is_refused(use_case, owner, account, service_account_repository):
    service_account_repository.revoke([account.id], NOW)

    with pytest.raises(ServiceAccountAlreadyRevokedException):
        _rotate(use_case, owner, account.id)


def test_given_a_rotation_when_it_succeeds_then_it_is_audited_without_the_token(
    use_case, owner, account, service_account_event_repository
):
    rotated = _rotate(use_case, owner, account.id)

    event = service_account_event_repository.events[-1]
    assert event["event_type"] == "ServiceAccountTokenRotatedEvent"
    assert event["actor_user_id"] == OWNER_ID

    payload = json.dumps(event["event_data"])
    assert rotated.token not in payload
    assert hashlib.sha256(rotated.token.encode()).hexdigest() not in payload
