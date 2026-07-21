from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from password_management_context.application.commands import (
    ConsumeOneTimeLinkCommand,
    CreateOneTimeLinkCommand,
    ListMyOneTimeLinksCommand,
    ListOneTimeLinksForAdminCommand,
    RevokeAllOneTimeLinksForUserCommand,
    RevokeOneTimeLinkCommand,
    RevokeOneTimeLinkForAdminCommand,
)
from password_management_context.application.services import (
    OneTimeLinkAuditAssembler,
    PasswordOwnershipService,
)
from password_management_context.application.use_cases import (
    ConsumeOneTimeLinkUseCase,
    CreateOneTimeLinkUseCase,
    ListMyOneTimeLinksUseCase,
    ListOneTimeLinksForAdminUseCase,
    RevokeAllOneTimeLinksForUserUseCase,
    RevokeOneTimeLinkForAdminUseCase,
    RevokeOneTimeLinkUseCase,
)
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import (
    NotPasswordOwnerError,
    OneTimeLinkNotFoundError,
    OneTimeLinkRevokedError,
)
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import AuthenticatedUser
from shared_kernel.domain.value_objects import ADMIN_ROLE
from tests.shared_kernel.fakes import FakeTimeGateway

from ..fakes import (
    FakeUserInfoGateway,
)

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

ALICE = UUID("00000000-0000-0000-0000-0000000000a1")
BOB = UUID("00000000-0000-0000-0000-0000000000a2")
GROUP_ID = UUID("00000000-0000-0000-0000-0000000000b1")
PASSWORD_ID = UUID("00000000-0000-0000-0000-0000000000c1")

ADMIN = AuthenticatedUser(user_id=UUID("00000000-0000-0000-0000-0000000000f1"), roles=[ADMIN_ROLE])
PLAIN_USER = AuthenticatedUser(user_id=ALICE, roles=[])


@pytest.fixture
def time_gateway():
    return FakeTimeGateway(fixed_time=T0)


@pytest.fixture
def user_info_gateway():
    return FakeUserInfoGateway()


@pytest.fixture
def audit_assembler(password_repository, password_permissions_repository, user_info_gateway):
    return OneTimeLinkAuditAssembler(password_repository, password_permissions_repository, user_info_gateway)


@pytest.fixture
def owned_password(password_repository, password_permissions_repository, group_access_gateway):
    """A password owned by GROUP_ID, which Alice owns."""
    password = Password.create(id=PASSWORD_ID, name="Prod DB", encrypted_value="encrypted(s3cret)")
    password_repository.save(password)
    password_permissions_repository.set_owner(GROUP_ID, PASSWORD_ID)
    group_access_gateway.set_group_owner(GROUP_ID, ALICE)
    return password


@pytest.fixture
def ownership_service(password_repository, password_permissions_repository, group_access_gateway):
    return PasswordOwnershipService(password_repository, password_permissions_repository, group_access_gateway)


@pytest.fixture
def create_use_case(one_time_link_repository, ownership_service, password_event_repository, time_gateway):
    return CreateOneTimeLinkUseCase(
        one_time_link_repository, ownership_service, password_event_repository, time_gateway
    )


@pytest.fixture
def consume_use_case(
    one_time_link_repository,
    password_repository,
    password_encryption_gateway,
    password_vault_access_gateway,
    password_event_repository,
    time_gateway,
):
    return ConsumeOneTimeLinkUseCase(
        one_time_link_repository,
        password_repository,
        password_encryption_gateway,
        password_vault_access_gateway,
        password_event_repository,
        time_gateway,
    )


@pytest.fixture
def admin_list_use_case(one_time_link_repository, audit_assembler, time_gateway):
    return ListOneTimeLinksForAdminUseCase(one_time_link_repository, audit_assembler, time_gateway)


@pytest.fixture
def my_list_use_case(one_time_link_repository, audit_assembler, time_gateway):
    return ListMyOneTimeLinksUseCase(one_time_link_repository, audit_assembler, time_gateway)


@pytest.fixture
def admin_revoke_use_case(one_time_link_repository, time_gateway):
    return RevokeOneTimeLinkForAdminUseCase(one_time_link_repository, time_gateway)


@pytest.fixture
def admin_revoke_all_use_case(one_time_link_repository, time_gateway):
    return RevokeAllOneTimeLinksForUserUseCase(one_time_link_repository, time_gateway)


@pytest.fixture
def revoke_use_case(one_time_link_repository, ownership_service, time_gateway):
    return RevokeOneTimeLinkUseCase(one_time_link_repository, ownership_service, time_gateway)


def _issue(create_use_case, user_id=ALICE, password_id=PASSWORD_ID):
    return create_use_case.execute(CreateOneTimeLinkCommand(password_id=password_id, requesting_user_id=user_id))


# ── Admin listing ─────────────────────────────────────────────────────


def test_non_admin_cannot_list_every_link(admin_list_use_case):
    with pytest.raises(NotAdminError):
        admin_list_use_case.execute(ListOneTimeLinksForAdminCommand(requesting_user=PLAIN_USER))


def test_admin_listing_spans_every_password_and_names_the_issuer_and_group(
    create_use_case, admin_list_use_case, user_info_gateway, owned_password
):
    user_info_gateway.set_user_display_name(ALICE, "Alice Martin")
    user_info_gateway.set_group_name(GROUP_ID, "Platform team")
    _issue(create_use_case)

    result = admin_list_use_case.execute(ListOneTimeLinksForAdminCommand(requesting_user=ADMIN))

    assert result.total == 1
    # The display name, not the email: the tables identify people the way the
    # rest of the app does.
    assert result.links[0].created_by_display_name == "Alice Martin"
    assert result.links[0].password_name == "Prod DB"
    assert result.links[0].group_name == "Platform team"


def test_admin_listing_hides_spent_links_unless_asked(
    create_use_case, consume_use_case, admin_list_use_case, owned_password
):
    consume_use_case.execute(ConsumeOneTimeLinkCommand(token=_issue(create_use_case).token))

    active_only = admin_list_use_case.execute(ListOneTimeLinksForAdminCommand(requesting_user=ADMIN))
    assert active_only.links == []

    with_history = admin_list_use_case.execute(
        ListOneTimeLinksForAdminCommand(requesting_user=ADMIN, include_inactive=True)
    )
    assert len(with_history.links) == 1


def test_admin_listing_reports_a_deleted_password_without_a_name(
    create_use_case, admin_list_use_case, password_repository, owned_password
):
    """The link outlives its password, so the row must still render."""
    _issue(create_use_case)
    password_repository.delete(PASSWORD_ID)

    result = admin_list_use_case.execute(ListOneTimeLinksForAdminCommand(requesting_user=ADMIN))

    assert result.links[0].password_name is None


# ── Personal listing ──────────────────────────────────────────────────


def test_my_listing_returns_only_my_own_links(create_use_case, my_list_use_case, group_access_gateway, owned_password):
    group_access_gateway.set_group_owner(GROUP_ID, BOB)
    _issue(create_use_case, user_id=ALICE)
    _issue(create_use_case, user_id=BOB)

    result = my_list_use_case.execute(ListMyOneTimeLinksCommand(requesting_user_id=ALICE))

    assert len(result.links) == 1
    assert result.links[0].created_by_user_id == ALICE
    assert result.total == 1


def test_personal_listing_still_names_the_owning_group(
    create_use_case, my_list_use_case, user_info_gateway, owned_password
):
    """The group matters on both tables: it says who else can reach the secret."""
    user_info_gateway.set_group_name(GROUP_ID, "Platform team")
    _issue(create_use_case, user_id=ALICE)

    result = my_list_use_case.execute(ListMyOneTimeLinksCommand(requesting_user_id=ALICE))

    assert result.links[0].group_name == "Platform team"
    # No issuer on the personal table: there is only one, and it is the reader.
    assert result.links[0].created_by_display_name is None


# ── Admin revocation ──────────────────────────────────────────────────


def test_non_admin_cannot_revoke_someone_elses_link(admin_revoke_use_case):
    with pytest.raises(NotAdminError):
        admin_revoke_use_case.execute(RevokeOneTimeLinkForAdminCommand(link_id=uuid4(), requesting_user=PLAIN_USER))


def test_admin_revokes_a_link_they_do_not_own(create_use_case, admin_revoke_use_case, consume_use_case, owned_password):
    created = _issue(create_use_case)

    admin_revoke_use_case.execute(RevokeOneTimeLinkForAdminCommand(link_id=created.id, requesting_user=ADMIN))

    with pytest.raises(OneTimeLinkRevokedError):
        consume_use_case.execute(ConsumeOneTimeLinkCommand(token=created.token))


def test_admin_revoking_an_already_read_link_is_refused(
    create_use_case, consume_use_case, admin_revoke_use_case, one_time_link_repository, owned_password
):
    created = _issue(create_use_case)
    consume_use_case.execute(ConsumeOneTimeLinkCommand(token=created.token))

    with pytest.raises(OneTimeLinkNotFoundError):
        admin_revoke_use_case.execute(RevokeOneTimeLinkForAdminCommand(link_id=created.id, requesting_user=ADMIN))

    # The read timestamp is audit data and must survive the attempt.
    assert one_time_link_repository.storage[created.id].read_at == T0


# ── Bulk revocation ───────────────────────────────────────────────────


def test_non_admin_cannot_bulk_revoke(admin_revoke_all_use_case):
    with pytest.raises(NotAdminError):
        admin_revoke_all_use_case.execute(
            RevokeAllOneTimeLinksForUserCommand(target_user_id=ALICE, requesting_user=PLAIN_USER)
        )


def test_bulk_revocation_cuts_only_the_targeted_users_live_links(
    create_use_case,
    consume_use_case,
    admin_revoke_all_use_case,
    one_time_link_repository,
    group_access_gateway,
    owned_password,
):
    group_access_gateway.set_group_owner(GROUP_ID, BOB)
    alice_live = _issue(create_use_case, user_id=ALICE)
    alice_read = _issue(create_use_case, user_id=ALICE)
    consume_use_case.execute(ConsumeOneTimeLinkCommand(token=alice_read.token))
    bob_live = _issue(create_use_case, user_id=BOB)

    revoked = admin_revoke_all_use_case.execute(
        RevokeAllOneTimeLinksForUserCommand(target_user_id=ALICE, requesting_user=ADMIN)
    )

    assert revoked == 1
    assert one_time_link_repository.storage[alice_live.id].is_revoked()
    # An already-read link keeps its trail rather than being marked revoked.
    assert one_time_link_repository.storage[alice_read.id].read_at == T0
    assert not one_time_link_repository.storage[alice_read.id].is_revoked()
    assert not one_time_link_repository.storage[bob_live.id].is_revoked()


# ── The rule this feature exists for ──────────────────────────────────


def test_issuer_can_revoke_their_own_link_after_losing_ownership(
    create_use_case, revoke_use_case, one_time_link_repository, group_access_gateway, owned_password
):
    """Someone leaves a team and loses ownership of the password. They must still
    be able to cut the link they handed out, or it outlives their access with no
    way for them to stop it."""
    created = _issue(create_use_case, user_id=ALICE)
    group_access_gateway._group_owners[GROUP_ID].discard(ALICE)

    revoke_use_case.execute(RevokeOneTimeLinkCommand(link_id=created.id, requesting_user_id=ALICE))

    assert one_time_link_repository.storage[created.id].is_revoked()


def test_a_stranger_still_cannot_revoke_someone_elses_link(create_use_case, revoke_use_case, owned_password):
    created = _issue(create_use_case, user_id=ALICE)

    with pytest.raises(NotPasswordOwnerError):
        revoke_use_case.execute(RevokeOneTimeLinkCommand(link_id=created.id, requesting_user_id=BOB))


def test_expired_links_drop_out_of_both_listings(
    create_use_case, admin_list_use_case, my_list_use_case, time_gateway, owned_password
):
    create_use_case.execute(
        CreateOneTimeLinkCommand(password_id=PASSWORD_ID, requesting_user_id=ALICE, lifetime_seconds=600)
    )
    time_gateway.set_current_time(T0 + timedelta(seconds=601))

    assert admin_list_use_case.execute(ListOneTimeLinksForAdminCommand(requesting_user=ADMIN)).links == []
    assert my_list_use_case.execute(ListMyOneTimeLinksCommand(requesting_user_id=ALICE)).links == []
