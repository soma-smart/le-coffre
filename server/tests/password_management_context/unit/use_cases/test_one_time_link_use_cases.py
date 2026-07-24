from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from password_management_context.application.commands import (
    ConsumeOneTimeLinkCommand,
    CreateOneTimeLinkCommand,
    ListOneTimeLinksCommand,
    RevokeOneTimeLinkCommand,
)
from password_management_context.application.services import PasswordOwnershipService
from password_management_context.application.use_cases import (
    ConsumeOneTimeLinkUseCase,
    CreateOneTimeLinkUseCase,
    ListOneTimeLinksUseCase,
    RevokeOneTimeLinkUseCase,
)
from password_management_context.application.use_cases.one_time_link.list_one_time_links_use_case import (
    MAX_LISTED_LINKS,
)
from password_management_context.domain.entities import Password
from password_management_context.domain.entities.one_time_link import MAX_ACTIVE_LINKS_PER_PASSWORD
from password_management_context.domain.exceptions import (
    NotPasswordOwnerError,
    OneTimeLinkAlreadyUsedError,
    OneTimeLinkExpiredError,
    OneTimeLinkLifetimeTooLongError,
    OneTimeLinkNotFoundError,
    OneTimeLinkRevokedError,
    PasswordEncryptionUnavailableError,
    PasswordNotFoundError,
    TooManyActiveOneTimeLinksError,
)
from password_management_context.domain.value_objects import OneTimeLinkToken
from tests.shared_kernel.fakes import FakeTimeGateway

from ..fakes import (
    FakeGroupAccessGateway,
    FakeOneTimeLinkRepository,
    FakePasswordEncryptionGateway,
    FakePasswordEventRepository,
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
    FakePasswordVaultAccessGateway,
)

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

OWNER_ID = UUID("00000000-0000-0000-0000-0000000000a1")
OUTSIDER_ID = UUID("00000000-0000-0000-0000-0000000000a2")
GROUP_ID = UUID("00000000-0000-0000-0000-0000000000b1")
PASSWORD_ID = UUID("00000000-0000-0000-0000-0000000000c1")


@pytest.fixture
def time_gateway():
    return FakeTimeGateway(fixed_time=T0)


@pytest.fixture
def owned_password(
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
) -> Password:
    """A password owned by GROUP_ID, itself owned by OWNER_ID."""
    password = Password.create(
        id=PASSWORD_ID,
        name="Production database",
        encrypted_value="encrypted(s3cret-value)",
        login="dba",
        url="https://db.example.com",
    )
    password_repository.save(password)
    password_permissions_repository.set_owner(GROUP_ID, PASSWORD_ID)
    group_access_gateway.set_group_owner(GROUP_ID, OWNER_ID)
    return password


@pytest.fixture
def create_use_case(
    one_time_link_repository: FakeOneTimeLinkRepository,
    password_ownership_service: PasswordOwnershipService,
    password_event_repository: FakePasswordEventRepository,
    time_gateway: FakeTimeGateway,
):
    return CreateOneTimeLinkUseCase(
        one_time_link_repository,
        password_ownership_service,
        password_event_repository,
        time_gateway,
    )


@pytest.fixture
def consume_use_case(
    one_time_link_repository: FakeOneTimeLinkRepository,
    password_repository: FakePasswordRepository,
    password_encryption_gateway: FakePasswordEncryptionGateway,
    password_vault_access_gateway: FakePasswordVaultAccessGateway,
    password_event_repository: FakePasswordEventRepository,
    time_gateway: FakeTimeGateway,
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
def list_use_case(
    one_time_link_repository: FakeOneTimeLinkRepository,
    password_ownership_service: PasswordOwnershipService,
    time_gateway: FakeTimeGateway,
):
    return ListOneTimeLinksUseCase(one_time_link_repository, password_ownership_service, time_gateway)


@pytest.fixture
def revoke_use_case(
    one_time_link_repository: FakeOneTimeLinkRepository,
    password_ownership_service: PasswordOwnershipService,
    time_gateway: FakeTimeGateway,
):
    return RevokeOneTimeLinkUseCase(one_time_link_repository, password_ownership_service, time_gateway)


# ── Creation ──────────────────────────────────────────────────────────


def test_given_owner_when_creating_should_return_a_token_and_store_only_its_hash(
    create_use_case: CreateOneTimeLinkUseCase,
    one_time_link_repository: FakeOneTimeLinkRepository,
    owned_password: Password,
):
    result = create_use_case.execute(CreateOneTimeLinkCommand(password_id=PASSWORD_ID, requesting_user_id=OWNER_ID))

    assert result.expires_at == T0 + timedelta(days=1)
    stored = one_time_link_repository.storage[result.id]
    assert stored.token_hash == OneTimeLinkToken(value=result.token).hashed()
    assert result.token not in stored.token_hash


def test_given_non_owner_when_creating_should_raise(
    create_use_case: CreateOneTimeLinkUseCase,
    one_time_link_repository: FakeOneTimeLinkRepository,
    owned_password: Password,
):
    with pytest.raises(NotPasswordOwnerError):
        create_use_case.execute(CreateOneTimeLinkCommand(password_id=PASSWORD_ID, requesting_user_id=OUTSIDER_ID))

    assert one_time_link_repository.storage == {}


def test_given_group_member_who_is_not_group_owner_when_creating_should_raise(
    create_use_case: CreateOneTimeLinkUseCase,
    group_access_gateway: FakeGroupAccessGateway,
    owned_password: Password,
):
    """Read access is not enough: issuing a link is an owner-level act."""
    group_access_gateway.add_group_member(GROUP_ID, OUTSIDER_ID)

    with pytest.raises(NotPasswordOwnerError):
        create_use_case.execute(CreateOneTimeLinkCommand(password_id=PASSWORD_ID, requesting_user_id=OUTSIDER_ID))


def test_given_unknown_password_when_creating_should_raise(
    create_use_case: CreateOneTimeLinkUseCase,
):
    with pytest.raises(PasswordNotFoundError):
        create_use_case.execute(CreateOneTimeLinkCommand(password_id=uuid4(), requesting_user_id=OWNER_ID))


def test_given_out_of_range_lifetime_when_creating_should_raise_and_store_nothing(
    create_use_case: CreateOneTimeLinkUseCase,
    one_time_link_repository: FakeOneTimeLinkRepository,
    owned_password: Password,
):
    with pytest.raises(OneTimeLinkLifetimeTooLongError):
        create_use_case.execute(
            CreateOneTimeLinkCommand(
                password_id=PASSWORD_ID,
                requesting_user_id=OWNER_ID,
                lifetime_seconds=30 * 24 * 60 * 60,
            )
        )

    assert one_time_link_repository.storage == {}


def test_given_creation_when_succeeding_should_record_an_audit_event(
    create_use_case: CreateOneTimeLinkUseCase,
    password_event_repository: FakePasswordEventRepository,
    owned_password: Password,
):
    create_use_case.execute(CreateOneTimeLinkCommand(password_id=PASSWORD_ID, requesting_user_id=OWNER_ID))

    event = password_event_repository.events[-1]
    assert event["event_type"] == "OneTimeLinkCreatedEvent"
    assert event["actor_user_id"] == OWNER_ID
    assert event["password_id"] == PASSWORD_ID


# ── Consumption ───────────────────────────────────────────────────────


def _issue_link(create_use_case: CreateOneTimeLinkUseCase, lifetime_seconds: int | None = None) -> str:
    result = create_use_case.execute(
        CreateOneTimeLinkCommand(
            password_id=PASSWORD_ID,
            requesting_user_id=OWNER_ID,
            lifetime_seconds=lifetime_seconds,
        )
    )
    return result.token


def test_given_a_fresh_link_when_consuming_should_return_secret_and_metadata(
    create_use_case: CreateOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    owned_password: Password,
):
    token = _issue_link(create_use_case)

    result = consume_use_case.execute(ConsumeOneTimeLinkCommand(token=token))

    assert result.password == "s3cret-value"
    assert result.name == "Production database"
    assert result.login == "dba"
    assert result.url == "https://db.example.com"


def test_given_a_link_consumed_once_when_consuming_again_should_raise(
    create_use_case: CreateOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    owned_password: Password,
):
    token = _issue_link(create_use_case)
    consume_use_case.execute(ConsumeOneTimeLinkCommand(token=token))

    with pytest.raises(OneTimeLinkAlreadyUsedError):
        consume_use_case.execute(ConsumeOneTimeLinkCommand(token=token))


def test_given_an_expired_link_when_consuming_should_raise(
    create_use_case: CreateOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    time_gateway: FakeTimeGateway,
    owned_password: Password,
):
    token = _issue_link(create_use_case, lifetime_seconds=600)
    time_gateway.set_current_time(T0 + timedelta(seconds=601))

    with pytest.raises(OneTimeLinkExpiredError):
        consume_use_case.execute(ConsumeOneTimeLinkCommand(token=token))


def test_given_an_unknown_token_when_consuming_should_raise(
    consume_use_case: ConsumeOneTimeLinkUseCase,
):
    with pytest.raises(OneTimeLinkNotFoundError):
        consume_use_case.execute(ConsumeOneTimeLinkCommand(token=OneTimeLinkToken.generate().value))


def test_given_a_locked_vault_when_consuming_should_raise_and_leave_the_link_usable(
    create_use_case: CreateOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    password_vault_access_gateway: FakePasswordVaultAccessGateway,
    one_time_link_repository: FakeOneTimeLinkRepository,
    owned_password: Password,
):
    """A locked vault is an operational incident, not the recipient's fault:
    it must not burn their single chance to read the secret."""
    token = _issue_link(create_use_case)
    password_vault_access_gateway.lock()

    with pytest.raises(PasswordEncryptionUnavailableError):
        consume_use_case.execute(ConsumeOneTimeLinkCommand(token=token))

    link = one_time_link_repository.get_by_token_hash(OneTimeLinkToken(value=token).hashed())
    assert link is not None
    assert not link.is_consumed()

    password_vault_access_gateway.unlock()
    assert consume_use_case.execute(ConsumeOneTimeLinkCommand(token=token)).password == "s3cret-value"


def test_given_a_deleted_password_when_consuming_should_report_an_unusable_link(
    create_use_case: CreateOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    password_repository: FakePasswordRepository,
    owned_password: Password,
):
    """The anonymous caller must not learn that the password once existed."""
    token = _issue_link(create_use_case)
    password_repository.delete(PASSWORD_ID)

    with pytest.raises(OneTimeLinkNotFoundError):
        consume_use_case.execute(ConsumeOneTimeLinkCommand(token=token))


def test_given_consumption_when_succeeding_should_record_a_read_event_attributed_to_the_creator(
    create_use_case: CreateOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    password_event_repository: FakePasswordEventRepository,
    owned_password: Password,
):
    token = _issue_link(create_use_case)
    consume_use_case.execute(ConsumeOneTimeLinkCommand(token=token))

    event = password_event_repository.events[-1]
    assert event["event_type"] == "OneTimeLinkReadEvent"
    assert event["actor_user_id"] == OWNER_ID
    assert event["event_data"]["actor"] == "anonymous"


def test_given_consumption_when_succeeding_should_not_store_the_secret_in_the_event(
    create_use_case: CreateOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    password_event_repository: FakePasswordEventRepository,
    owned_password: Password,
):
    token = _issue_link(create_use_case)
    consume_use_case.execute(ConsumeOneTimeLinkCommand(token=token))

    serialized = str(password_event_repository.events[-1])
    assert "s3cret-value" not in serialized
    assert token not in serialized


# ── Revocation ────────────────────────────────────────────────────────


def test_given_owner_when_revoking_should_make_the_link_unusable(
    create_use_case: CreateOneTimeLinkUseCase,
    revoke_use_case: RevokeOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    one_time_link_repository: FakeOneTimeLinkRepository,
    owned_password: Password,
):
    token = _issue_link(create_use_case)
    link_id = next(iter(one_time_link_repository.storage))

    revoke_use_case.execute(RevokeOneTimeLinkCommand(link_id=link_id, requesting_user_id=OWNER_ID))

    with pytest.raises(OneTimeLinkRevokedError):
        consume_use_case.execute(ConsumeOneTimeLinkCommand(token=token))


def test_given_non_owner_when_revoking_should_raise(
    create_use_case: CreateOneTimeLinkUseCase,
    revoke_use_case: RevokeOneTimeLinkUseCase,
    one_time_link_repository: FakeOneTimeLinkRepository,
    owned_password: Password,
):
    _issue_link(create_use_case)
    link_id = next(iter(one_time_link_repository.storage))

    with pytest.raises(NotPasswordOwnerError):
        revoke_use_case.execute(RevokeOneTimeLinkCommand(link_id=link_id, requesting_user_id=OUTSIDER_ID))


def test_given_an_already_read_link_when_revoking_should_raise_and_keep_the_read_timestamp(
    create_use_case: CreateOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    revoke_use_case: RevokeOneTimeLinkUseCase,
    one_time_link_repository: FakeOneTimeLinkRepository,
    owned_password: Password,
):
    """Revoking must never erase the audit trail of an actual read."""
    token = _issue_link(create_use_case)
    consume_use_case.execute(ConsumeOneTimeLinkCommand(token=token))
    link_id = next(iter(one_time_link_repository.storage))

    with pytest.raises(OneTimeLinkNotFoundError):
        revoke_use_case.execute(RevokeOneTimeLinkCommand(link_id=link_id, requesting_user_id=OWNER_ID))

    link = one_time_link_repository.storage[link_id]
    assert link.read_at == T0
    assert link.revoked_at is None


def test_given_unknown_link_when_revoking_should_raise(
    revoke_use_case: RevokeOneTimeLinkUseCase,
):
    with pytest.raises(OneTimeLinkNotFoundError):
        revoke_use_case.execute(RevokeOneTimeLinkCommand(link_id=uuid4(), requesting_user_id=OWNER_ID))


# ── Listing ───────────────────────────────────────────────────────────


def test_given_owner_when_listing_should_return_summaries_without_any_token(
    create_use_case: CreateOneTimeLinkUseCase,
    list_use_case: ListOneTimeLinksUseCase,
    owned_password: Password,
):
    token = _issue_link(create_use_case)

    result = list_use_case.execute(ListOneTimeLinksCommand(password_id=PASSWORD_ID, requesting_user_id=OWNER_ID))

    assert len(result.links) == 1
    assert result.total == 1
    assert token not in str(result.links[0])
    assert not hasattr(result.links[0], "token_hash")


def test_given_a_consumed_link_when_listing_should_expose_when_it_was_read(
    create_use_case: CreateOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    list_use_case: ListOneTimeLinksUseCase,
    owned_password: Password,
):
    token = _issue_link(create_use_case)
    consume_use_case.execute(ConsumeOneTimeLinkCommand(token=token))

    default_result = list_use_case.execute(
        ListOneTimeLinksCommand(password_id=PASSWORD_ID, requesting_user_id=OWNER_ID)
    )
    assert default_result.links == []

    with_history = list_use_case.execute(
        ListOneTimeLinksCommand(password_id=PASSWORD_ID, requesting_user_id=OWNER_ID, include_inactive=True)
    )
    assert with_history.links[0].read_at == T0


def test_given_many_links_when_listing_should_cap_the_page_but_report_the_true_total(
    create_use_case: CreateOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    list_use_case: ListOneTimeLinksUseCase,
    owned_password: Password,
):
    """Read and revoked links are kept forever, so a long-lived password
    accumulates them without bound. The listing has to stay small, and it has to
    say how many exist rather than let the owner believe they see everything."""
    # Consumed right away so each creation frees its slot: this is how a
    # password accumulates history in real use, and it is that history, not the
    # active links, that the listing bound exists to contain.
    for _ in range(MAX_LISTED_LINKS + 15):
        consume_use_case.execute(ConsumeOneTimeLinkCommand(token=_issue_link(create_use_case)))

    result = list_use_case.execute(
        ListOneTimeLinksCommand(password_id=PASSWORD_ID, requesting_user_id=OWNER_ID, include_inactive=True)
    )

    assert len(result.links) == MAX_LISTED_LINKS
    assert result.total == MAX_LISTED_LINKS + 15
    assert result.active == 0


def test_given_non_owner_when_listing_should_raise(
    list_use_case: ListOneTimeLinksUseCase,
    owned_password: Password,
):
    with pytest.raises(NotPasswordOwnerError):
        list_use_case.execute(ListOneTimeLinksCommand(password_id=PASSWORD_ID, requesting_user_id=OUTSIDER_ID))


# ── Cap on simultaneously active links ────────────────────────────────


def test_given_the_cap_is_reached_when_creating_should_refuse(
    create_use_case: CreateOneTimeLinkUseCase,
    one_time_link_repository: FakeOneTimeLinkRepository,
    owned_password: Password,
):
    """Each active link is a live anonymous read grant on the same secret, and
    each has to be revoked one by one. The cap bounds that exposure."""
    for _ in range(MAX_ACTIVE_LINKS_PER_PASSWORD):
        _issue_link(create_use_case)

    with pytest.raises(TooManyActiveOneTimeLinksError) as excinfo:
        _issue_link(create_use_case)

    assert excinfo.value.active_count == MAX_ACTIVE_LINKS_PER_PASSWORD
    assert excinfo.value.max_active == MAX_ACTIVE_LINKS_PER_PASSWORD
    assert len(one_time_link_repository.storage) == MAX_ACTIVE_LINKS_PER_PASSWORD


def test_given_a_link_was_read_when_creating_should_free_a_slot(
    create_use_case: CreateOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    owned_password: Password,
):
    """A spent link is no longer a grant, so it must not keep occupying a slot;
    otherwise an owner sharing regularly would be permanently locked out."""
    tokens = [_issue_link(create_use_case) for _ in range(MAX_ACTIVE_LINKS_PER_PASSWORD)]
    consume_use_case.execute(ConsumeOneTimeLinkCommand(token=tokens[0]))

    _issue_link(create_use_case)  # must not raise


def test_given_a_link_was_revoked_when_creating_should_free_a_slot(
    create_use_case: CreateOneTimeLinkUseCase,
    revoke_use_case: RevokeOneTimeLinkUseCase,
    one_time_link_repository: FakeOneTimeLinkRepository,
    owned_password: Password,
):
    for _ in range(MAX_ACTIVE_LINKS_PER_PASSWORD):
        _issue_link(create_use_case)
    link_id = next(iter(one_time_link_repository.storage))
    revoke_use_case.execute(RevokeOneTimeLinkCommand(link_id=link_id, requesting_user_id=OWNER_ID))

    _issue_link(create_use_case)  # must not raise


def test_given_links_expired_when_creating_should_free_their_slots(
    create_use_case: CreateOneTimeLinkUseCase,
    time_gateway: FakeTimeGateway,
    owned_password: Password,
):
    for _ in range(MAX_ACTIVE_LINKS_PER_PASSWORD):
        _issue_link(create_use_case, lifetime_seconds=600)
    time_gateway.set_current_time(T0 + timedelta(seconds=601))

    _issue_link(create_use_case)  # must not raise


def test_the_cap_is_per_password_not_global(
    create_use_case: CreateOneTimeLinkUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    owned_password: Password,
):
    other_id = uuid4()
    password_repository.save(Password.create(id=other_id, name="other", encrypted_value="encrypted(x)"))
    password_permissions_repository.set_owner(GROUP_ID, other_id)
    for _ in range(MAX_ACTIVE_LINKS_PER_PASSWORD):
        _issue_link(create_use_case)

    create_use_case.execute(
        CreateOneTimeLinkCommand(password_id=other_id, requesting_user_id=OWNER_ID)
    )  # must not raise


def test_listing_reports_how_much_of_the_cap_is_used(
    create_use_case: CreateOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    list_use_case: ListOneTimeLinksUseCase,
    owned_password: Password,
):
    tokens = [_issue_link(create_use_case) for _ in range(3)]
    consume_use_case.execute(ConsumeOneTimeLinkCommand(token=tokens[0]))

    result = list_use_case.execute(ListOneTimeLinksCommand(password_id=PASSWORD_ID, requesting_user_id=OWNER_ID))

    assert result.active == 2
    assert result.total == 3
    assert result.max_active == MAX_ACTIVE_LINKS_PER_PASSWORD


def test_default_listing_shows_only_links_the_owner_can_still_act_on(
    create_use_case: CreateOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    revoke_use_case: RevokeOneTimeLinkUseCase,
    list_use_case: ListOneTimeLinksUseCase,
    owned_password: Password,
):
    alive = create_use_case.execute(CreateOneTimeLinkCommand(password_id=PASSWORD_ID, requesting_user_id=OWNER_ID))
    consume_use_case.execute(ConsumeOneTimeLinkCommand(token=_issue_link(create_use_case)))
    to_revoke = create_use_case.execute(CreateOneTimeLinkCommand(password_id=PASSWORD_ID, requesting_user_id=OWNER_ID))
    revoke_use_case.execute(RevokeOneTimeLinkCommand(link_id=to_revoke.id, requesting_user_id=OWNER_ID))

    result = list_use_case.execute(ListOneTimeLinksCommand(password_id=PASSWORD_ID, requesting_user_id=OWNER_ID))

    assert [link.id for link in result.links] == [alive.id]
    # The counters still describe the whole set, so the owner is not misled into
    # thinking only one link was ever issued.
    assert result.total == 3
    assert result.active == 1


def test_default_listing_surfaces_an_active_link_hidden_behind_newer_spent_ones(
    create_use_case: CreateOneTimeLinkUseCase,
    consume_use_case: ConsumeOneTimeLinkUseCase,
    list_use_case: ListOneTimeLinksUseCase,
    owned_password: Password,
):
    """The filter has to run in the query. Trimming a page of recent links would
    drop this one, and the owner could no longer revoke it from the UI."""
    old_active = create_use_case.execute(CreateOneTimeLinkCommand(password_id=PASSWORD_ID, requesting_user_id=OWNER_ID))
    for _ in range(MAX_LISTED_LINKS + 5):
        consume_use_case.execute(ConsumeOneTimeLinkCommand(token=_issue_link(create_use_case)))

    result = list_use_case.execute(ListOneTimeLinksCommand(password_id=PASSWORD_ID, requesting_user_id=OWNER_ID))

    assert [link.id for link in result.links] == [old_active.id]


def test_expired_links_drop_out_of_the_default_listing(
    create_use_case: CreateOneTimeLinkUseCase,
    time_gateway: FakeTimeGateway,
    list_use_case: ListOneTimeLinksUseCase,
    owned_password: Password,
):
    _issue_link(create_use_case, lifetime_seconds=600)
    time_gateway.set_current_time(T0 + timedelta(seconds=601))

    result = list_use_case.execute(ListOneTimeLinksCommand(password_id=PASSWORD_ID, requesting_user_id=OWNER_ID))

    assert result.links == []
    assert result.active == 0
    assert result.total == 1
