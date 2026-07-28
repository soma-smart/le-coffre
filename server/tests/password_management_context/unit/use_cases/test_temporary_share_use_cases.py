from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from password_management_context.application.commands import (
    GetPasswordCommand,
    ListAccessCommand,
    ListPasswordEventsCommand,
    ListPasswordsCommand,
    ShareResourceCommand,
    UpdateShareExpirationCommand,
)
from password_management_context.application.use_cases import (
    GetPasswordUseCase,
    ListAccessUseCase,
    ListPasswordEventsUseCase,
    ListPasswordsUseCase,
    ShareAccessUseCase,
    UpdateShareExpirationUseCase,
)
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import (
    NotPasswordOwnerError,
    PasswordAccessDeniedError,
    ShareExpirationInPastError,
    ShareNotFoundError,
)
from password_management_context.domain.value_objects import PasswordPermission
from shared_kernel.domain.entities import AuthenticatedUser
from tests.fakes import FakeDomainEventPublisher
from tests.shared_kernel.fakes.fake_time_gateway import FakeTimeGateway

from ..conftest import NOW
from ..fakes import (
    FakeGroupAccessGateway,
    FakePasswordEncryptionGateway,
    FakePasswordEventRepository,
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
    FakePasswordVaultAccessGateway,
    FakeUserInfoGateway,
)

OWNER_ID = UUID("00000000-0000-0000-0000-00000000a001")
RECIPIENT_ID = UUID("00000000-0000-0000-0000-00000000a002")
OWNER_GROUP_ID = UUID("00000000-0000-0000-0000-00000000b001")
RECIPIENT_GROUP_ID = UUID("00000000-0000-0000-0000-00000000b002")

IN_ONE_HOUR = NOW + timedelta(hours=1)


@pytest.fixture
def password(password_repository: FakePasswordRepository) -> Password:
    pwd = Password(uuid4(), "prod-db", "encrypted_value", "default")
    password_repository.save(pwd)
    return pwd


@pytest.fixture(autouse=True)
def groups(
    password: Password,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
) -> None:
    password_permissions_repository.set_owner(OWNER_GROUP_ID, password.id)
    group_access_gateway.set_group_owner(OWNER_GROUP_ID, OWNER_ID)
    group_access_gateway.set_group_owner(RECIPIENT_GROUP_ID, RECIPIENT_ID)
    # The listing path derives timestamps from the creation event. Stored naive,
    # matching BasePasswordEvent.occurred_on, so the two sort together.
    password_event_repository.append_event(
        event_id=uuid4(),
        event_type="PasswordCreatedEvent",
        occurred_on=NOW.replace(tzinfo=None),
        password_id=password.id,
        actor_user_id=OWNER_ID,
        event_data={
            "password_id": str(password.id),
            "password_name": password.name,
            "owner_group_id": str(OWNER_GROUP_ID),
            "folder": password.folder,
        },
    )


@pytest.fixture
def share_use_case(
    password_repository,
    password_permissions_repository,
    group_access_gateway,
    domain_event_publisher: FakeDomainEventPublisher,
    password_event_repository: FakePasswordEventRepository,
    time_gateway: FakeTimeGateway,
) -> ShareAccessUseCase:
    return ShareAccessUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        domain_event_publisher,
        password_event_repository,
        time_gateway,
    )


@pytest.fixture
def update_use_case(
    password_repository,
    password_permissions_repository,
    group_access_gateway,
    domain_event_publisher: FakeDomainEventPublisher,
    password_event_repository: FakePasswordEventRepository,
    time_gateway: FakeTimeGateway,
) -> UpdateShareExpirationUseCase:
    return UpdateShareExpirationUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        domain_event_publisher,
        password_event_repository,
        time_gateway,
    )


@pytest.fixture
def get_use_case(
    password_repository,
    password_encryption_gateway: FakePasswordEncryptionGateway,
    password_permissions_repository,
    group_access_gateway,
    domain_event_publisher: FakeDomainEventPublisher,
    password_event_repository: FakePasswordEventRepository,
    time_gateway: FakeTimeGateway,
) -> GetPasswordUseCase:
    return GetPasswordUseCase(
        password_repository,
        password_encryption_gateway,
        password_permissions_repository,
        group_access_gateway,
        domain_event_publisher,
        password_event_repository,
        time_gateway,
    )


@pytest.fixture
def list_use_case(
    password_repository,
    password_permissions_repository,
    group_access_gateway,
    password_event_repository: FakePasswordEventRepository,
    time_gateway: FakeTimeGateway,
) -> ListPasswordsUseCase:
    return ListPasswordsUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        password_event_repository,
        time_gateway,
    )


@pytest.fixture
def list_access_use_case(
    password_repository,
    password_permissions_repository,
    group_access_gateway,
    time_gateway: FakeTimeGateway,
) -> ListAccessUseCase:
    return ListAccessUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        time_gateway,
        expired_share_retention_seconds=7 * 24 * 60 * 60,
    )


def _list_for(use_case: ListPasswordsUseCase, user_id: UUID):
    return use_case.execute(ListPasswordsCommand(requester=AuthenticatedUser(user_id=user_id, roles=[])))


# ── Sharing temporarily ───────────────────────────────────────────────


def test_should_share_permanently_when_no_expiry_is_given(
    share_use_case: ShareAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id))

    access = password_permissions_repository.list_all_permissions_for(password.id)[RECIPIENT_GROUP_ID]
    assert access.expires_at is None


def test_should_store_the_expiry_on_a_temporary_share(
    share_use_case: ShareAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))

    access = password_permissions_repository.list_all_permissions_for(password.id)[RECIPIENT_GROUP_ID]
    assert access.expires_at == IN_ONE_HOUR
    assert PasswordPermission.READ in access.permissions


def test_should_reject_an_expiry_in_the_past(share_use_case: ShareAccessUseCase, password: Password):
    with pytest.raises(ShareExpirationInPastError):
        share_use_case.execute(
            ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, NOW - timedelta(seconds=1))
        )


def test_should_record_the_expiry_on_the_shared_event(
    share_use_case: ShareAccessUseCase,
    password_event_repository: FakePasswordEventRepository,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))

    events = password_event_repository.list_events(password.id)
    shared = next(e for e in events if e["event_type"] == "PasswordSharedEvent")
    assert shared["event_data"]["expires_at"] == IN_ONE_HOUR.isoformat()


def test_should_overwrite_the_expiry_when_re_sharing(
    share_use_case: ShareAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))

    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id))

    access = password_permissions_repository.list_all_permissions_for(password.id)[RECIPIENT_GROUP_ID]
    assert access.expires_at is None


# ── Reading a temporarily shared password ─────────────────────────────


def test_recipient_can_read_before_the_deadline(
    share_use_case: ShareAccessUseCase,
    get_use_case: GetPasswordUseCase,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))

    assert get_use_case.execute(GetPasswordCommand(RECIPIENT_ID, password.id))


def test_recipient_loses_read_at_the_deadline(
    share_use_case: ShareAccessUseCase,
    get_use_case: GetPasswordUseCase,
    time_gateway: FakeTimeGateway,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))

    time_gateway.set_current_time(IN_ONE_HOUR)

    with pytest.raises(PasswordAccessDeniedError):
        get_use_case.execute(GetPasswordCommand(RECIPIENT_ID, password.id))


def test_owner_keeps_read_after_the_recipients_share_lapses(
    share_use_case: ShareAccessUseCase,
    get_use_case: GetPasswordUseCase,
    time_gateway: FakeTimeGateway,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))

    time_gateway.set_current_time(NOW + timedelta(days=400))

    assert get_use_case.execute(GetPasswordCommand(OWNER_ID, password.id))


def test_expired_share_drops_the_password_out_of_the_recipients_list(
    share_use_case: ShareAccessUseCase,
    list_use_case: ListPasswordsUseCase,
    time_gateway: FakeTimeGateway,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))
    assert len(_list_for(list_use_case, RECIPIENT_ID)) == 1

    time_gateway.set_current_time(IN_ONE_HOUR)

    assert _list_for(list_use_case, RECIPIENT_ID) == []


def test_should_report_the_deadline_of_the_recipients_own_access(
    share_use_case: ShareAccessUseCase,
    list_use_case: ListPasswordsUseCase,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))

    [entry] = _list_for(list_use_case, RECIPIENT_ID)
    assert entry.access_expires_at == IN_ONE_HOUR
    assert entry.can_write is False


def test_should_report_no_deadline_to_the_owner(
    share_use_case: ShareAccessUseCase,
    list_use_case: ListPasswordsUseCase,
    password: Password,
):
    """The owner's own access never lapses, whatever they granted to others."""
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))

    [entry] = _list_for(list_use_case, OWNER_ID)
    assert entry.access_expires_at is None
    assert entry.can_write is True


def test_expired_share_disappears_from_the_owners_accessible_group_ids(
    share_use_case: ShareAccessUseCase,
    list_use_case: ListPasswordsUseCase,
    time_gateway: FakeTimeGateway,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))
    assert RECIPIENT_GROUP_ID in _list_for(list_use_case, OWNER_ID)[0].accessible_group_ids

    time_gateway.set_current_time(IN_ONE_HOUR)

    assert RECIPIENT_GROUP_ID not in _list_for(list_use_case, OWNER_ID)[0].accessible_group_ids


# ── Retiming an existing share ────────────────────────────────────────


def test_owner_can_extend_a_temporary_share(
    share_use_case: ShareAccessUseCase,
    update_use_case: UpdateShareExpirationUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))
    later = NOW + timedelta(days=30)

    update_use_case.execute(UpdateShareExpirationCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, later))

    access = password_permissions_repository.list_all_permissions_for(password.id)[RECIPIENT_GROUP_ID]
    assert access.expires_at == later


def test_owner_can_make_a_temporary_share_permanent(
    share_use_case: ShareAccessUseCase,
    update_use_case: UpdateShareExpirationUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))

    update_use_case.execute(UpdateShareExpirationCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, None))

    access = password_permissions_repository.list_all_permissions_for(password.id)[RECIPIENT_GROUP_ID]
    assert access.expires_at is None


def test_owner_can_revive_a_share_that_already_lapsed(
    share_use_case: ShareAccessUseCase,
    update_use_case: UpdateShareExpirationUseCase,
    get_use_case: GetPasswordUseCase,
    time_gateway: FakeTimeGateway,
    password: Password,
):
    """Extending an expired-but-not-yet-purged share is the point of keeping it visible."""
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))
    time_gateway.set_current_time(IN_ONE_HOUR)

    update_use_case.execute(
        UpdateShareExpirationCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR + timedelta(days=7))
    )

    assert get_use_case.execute(GetPasswordCommand(RECIPIENT_ID, password.id))


def test_should_reject_retiming_by_a_non_owner(
    share_use_case: ShareAccessUseCase,
    update_use_case: UpdateShareExpirationUseCase,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))

    with pytest.raises(NotPasswordOwnerError):
        update_use_case.execute(
            UpdateShareExpirationCommand(RECIPIENT_ID, RECIPIENT_GROUP_ID, password.id, NOW + timedelta(days=30))
        )


def test_should_reject_retiming_a_share_that_does_not_exist(
    update_use_case: UpdateShareExpirationUseCase,
    password: Password,
):
    with pytest.raises(ShareNotFoundError):
        update_use_case.execute(
            UpdateShareExpirationCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, NOW + timedelta(days=30))
        )


def test_should_reject_retiming_the_owner_group(
    update_use_case: UpdateShareExpirationUseCase,
    password: Password,
):
    """Ownership carries no deadline, so it must not be reachable through this route."""
    with pytest.raises(ShareNotFoundError):
        update_use_case.execute(
            UpdateShareExpirationCommand(OWNER_ID, OWNER_GROUP_ID, password.id, NOW + timedelta(days=30))
        )


def test_should_record_both_dates_on_the_retiming_event(
    share_use_case: ShareAccessUseCase,
    update_use_case: UpdateShareExpirationUseCase,
    password_event_repository: FakePasswordEventRepository,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))

    update_use_case.execute(UpdateShareExpirationCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, None))

    events = password_event_repository.list_events(password.id)
    updated = next(e for e in events if e["event_type"] == "PasswordShareExpirationUpdatedEvent")
    assert updated["event_data"]["previous_expires_at"] == IN_ONE_HOUR.isoformat()
    assert updated["event_data"]["expires_at"] is None


# ── Listing access ────────────────────────────────────────────────────


def test_owner_still_sees_an_expired_share_in_the_access_list(
    share_use_case: ShareAccessUseCase,
    list_access_use_case: ListAccessUseCase,
    time_gateway: FakeTimeGateway,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))
    time_gateway.set_current_time(IN_ONE_HOUR)

    response = list_access_use_case.execute(ListAccessCommand(OWNER_ID, password.id))

    expired = next(g for g in response.group_accesses if g.group_id == RECIPIENT_GROUP_ID)
    assert expired.expires_at == IN_ONE_HOUR


def test_recipient_loses_the_access_list_once_their_share_lapses(
    share_use_case: ShareAccessUseCase,
    list_access_use_case: ListAccessUseCase,
    time_gateway: FakeTimeGateway,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))
    time_gateway.set_current_time(IN_ONE_HOUR)

    with pytest.raises(PasswordAccessDeniedError):
        list_access_use_case.execute(ListAccessCommand(RECIPIENT_ID, password.id))


def test_should_purge_shares_expired_beyond_the_retention_window(
    share_use_case: ShareAccessUseCase,
    list_access_use_case: ListAccessUseCase,
    time_gateway: FakeTimeGateway,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))
    time_gateway.set_current_time(IN_ONE_HOUR + timedelta(days=8))

    response = list_access_use_case.execute(ListAccessCommand(OWNER_ID, password.id))

    assert all(g.group_id != RECIPIENT_GROUP_ID for g in response.group_accesses)


def test_should_keep_a_recently_expired_share_within_the_retention_window(
    share_use_case: ShareAccessUseCase,
    list_access_use_case: ListAccessUseCase,
    time_gateway: FakeTimeGateway,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))
    time_gateway.set_current_time(IN_ONE_HOUR + timedelta(days=1))

    response = list_access_use_case.execute(ListAccessCommand(OWNER_ID, password.id))

    assert any(g.group_id == RECIPIENT_GROUP_ID for g in response.group_accesses)


# ── Reading the audit history ─────────────────────────────────────────


@pytest.fixture
def events_use_case(
    password_repository,
    password_permissions_repository,
    group_access_gateway,
    password_event_repository: FakePasswordEventRepository,
    password_vault_access_gateway: FakePasswordVaultAccessGateway,
    time_gateway: FakeTimeGateway,
) -> ListPasswordEventsUseCase:
    return ListPasswordEventsUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        password_event_repository,
        password_vault_access_gateway,
        FakeUserInfoGateway(),
        time_gateway,
    )


def test_recipient_can_read_the_history_before_the_deadline(
    share_use_case: ShareAccessUseCase,
    events_use_case: ListPasswordEventsUseCase,
    password: Password,
):
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))

    response = events_use_case.execute(
        ListPasswordEventsCommand(
            requesting_user=AuthenticatedUser(user_id=RECIPIENT_ID, roles=[]),
            password_id=password.id,
        )
    )

    assert response is not None


def test_expired_share_also_closes_the_audit_history(
    share_use_case: ShareAccessUseCase,
    events_use_case: ListPasswordEventsUseCase,
    time_gateway: FakeTimeGateway,
    password: Password,
):
    """The history names who reached the password and when it was shared.

    Losing the password but keeping its history would be a partial revocation.
    """
    share_use_case.execute(ShareResourceCommand(OWNER_ID, RECIPIENT_GROUP_ID, password.id, IN_ONE_HOUR))

    time_gateway.set_current_time(IN_ONE_HOUR)

    with pytest.raises(PasswordAccessDeniedError):
        events_use_case.execute(
            ListPasswordEventsCommand(
                requesting_user=AuthenticatedUser(user_id=RECIPIENT_ID, roles=[]),
                password_id=password.id,
            )
        )
