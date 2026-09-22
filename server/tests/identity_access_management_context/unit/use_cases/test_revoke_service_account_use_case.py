import dataclasses
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from identity_access_management_context.application.commands import (
    CreateServiceAccountCommand,
    RevokeServiceAccountCommand,
)
from identity_access_management_context.application.responses import ServiceAccountSummaryResponse
from identity_access_management_context.application.use_cases import (
    CreateServiceAccountUseCase,
    RevokeServiceAccountUseCase,
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
    return RevokeServiceAccountUseCase(
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


def _revoke(use_case, user, account_id):
    return use_case.execute(RevokeServiceAccountCommand(requesting_user=user, service_account_id=account_id))


def test_given_an_active_account_when_revoking_then_it_becomes_inactive(
    use_case, owner, account, service_account_repository, time_provider
):
    time_provider.set_current_time(LATER)

    _revoke(use_case, owner, account.id)

    stored = service_account_repository.accounts[account.id]
    assert not stored.is_active
    assert stored.revoked_at == LATER


def test_given_a_revoked_account_when_listing_the_group_then_the_row_survives(
    use_case, owner, account, service_account_repository
):
    _revoke(use_case, owner, account.id)

    remaining = list(service_account_repository.list_for_groups((GROUP_ID,)))
    assert [a.id for a in remaining] == [account.id]
    assert remaining[0].name == "nightly-backup"


def test_given_an_already_revoked_account_when_revoking_again_then_it_is_refused(use_case, owner, account):
    _revoke(use_case, owner, account.id)

    with pytest.raises(ServiceAccountAlreadyRevokedException):
        _revoke(use_case, owner, account.id)


def test_given_an_already_revoked_account_when_revoking_again_then_the_first_timestamp_stands(
    use_case, owner, account, service_account_repository, time_provider
):
    _revoke(use_case, owner, account.id)
    time_provider.set_current_time(LATER)

    with pytest.raises(ServiceAccountAlreadyRevokedException):
        _revoke(use_case, owner, account.id)

    assert service_account_repository.accounts[account.id].revoked_at == NOW


def test_given_a_plain_member_when_revoking_then_it_is_refused(use_case, account, groups):
    with pytest.raises(UserNotOwnerOfGroupException):
        _revoke(use_case, AuthenticatedUser(user_id=MEMBER_ID, roles=[]), account.id)


def test_given_an_unknown_account_when_revoking_then_it_is_not_found(use_case, owner, groups):
    with pytest.raises(ServiceAccountNotFoundException):
        _revoke(use_case, owner, uuid4())


def test_given_a_revocation_when_it_succeeds_then_it_is_audited_with_its_author(
    use_case, owner, account, service_account_event_repository
):
    _revoke(use_case, owner, account.id)

    event = service_account_event_repository.events[-1]
    assert event["event_type"] == "ServiceAccountRevokedEvent"
    assert event["actor_user_id"] == OWNER_ID
    assert account.token not in json.dumps(event["event_data"])


def test_the_summary_response_carries_no_token_field():
    """Pinned so a future field addition cannot quietly put the token in a listing."""
    names = {field.name for field in dataclasses.fields(ServiceAccountSummaryResponse)}

    assert not any("token" in name for name in names)
