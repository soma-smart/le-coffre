from datetime import timedelta
from uuid import UUID

import pytest

from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import AuthenticatedUser
from vault_management_context.application.commands import (
    AcknowledgeShareLinkCommand,
    GetShareLinksOverviewCommand,
    RetrieveShareLinkCommand,
)
from vault_management_context.application.use_cases import (
    AcknowledgeShareLinkUseCase,
    GetShareLinksOverviewUseCase,
    RetrieveShareLinkUseCase,
)
from vault_management_context.domain.entities import SHARE_LINK_LIFETIME, SHARE_LINK_REOPEN_WINDOW, Vault
from vault_management_context.domain.exceptions import VaultNotSetupException
from vault_management_context.domain.value_objects import ShareLinkStatus

from ..share_links import SETUP_ID, ack_key, issue_links, lookup

ADMIN = AuthenticatedUser(user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"])
USER = AuthenticatedUser(user_id=UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["user"])


@pytest.fixture()
def use_case(vault_repository, share_link_repository, vault_event_repository, time_gateway):
    return GetShareLinksOverviewUseCase(vault_repository, share_link_repository, vault_event_repository, time_gateway)


@pytest.fixture()
def retrieve_use_case(
    share_link_repository, event_publisher, vault_event_repository, time_gateway, transaction_gateway
):
    return RetrieveShareLinkUseCase(
        share_link_repository, event_publisher, vault_event_repository, time_gateway, transaction_gateway
    )


@pytest.fixture()
def acknowledge_use_case(
    share_link_repository, event_publisher, vault_event_repository, time_gateway, transaction_gateway
):
    return AcknowledgeShareLinkUseCase(
        share_link_repository, event_publisher, vault_event_repository, time_gateway, transaction_gateway
    )


@pytest.fixture()
def setup(vault_repository, share_link_repository, vault_event_repository, time_gateway):
    """A 3-share setup, links issued now, with the creation event the real setup records."""
    now = time_gateway.get_current_time()
    vault_repository.save(Vault(nb_shares=3, threshold=2, encrypted_key="key", setup_id=SETUP_ID, status="PENDING"))
    vault_event_repository.events.append(_created_event(SETUP_ID, now))
    return issue_links(share_link_repository, now)


def _created_event(setup_id, occurred_on):
    return {
        "event_id": UUID(int=1),
        "event_type": "VaultCreatedEvent",
        "occurred_on": occurred_on,
        "actor_user_id": None,
        "event_data": {"setup_id": setup_id, "nb_shares": 3, "threshold": 2},
    }


def _overview(use_case):
    return use_case.execute(GetShareLinksOverviewCommand(requesting_user=ADMIN))


def _statuses(overview):
    return [link.status for link in overview.links]


def _on_gateway_clock(vault_event_repository, time_gateway) -> None:
    """Events stamp themselves with the wall clock; the overview is judged on the gateway's."""
    vault_event_repository.events[-1]["occurred_on"] = time_gateway.get_current_time()


@pytest.fixture()
def retrieve(retrieve_use_case, vault_event_repository, time_gateway):
    def _retrieve(index: int) -> None:
        retrieve_use_case.execute(RetrieveShareLinkCommand(lookup_hash=lookup(f"token-{index}")))
        _on_gateway_clock(vault_event_repository, time_gateway)

    return _retrieve


@pytest.fixture()
def acknowledge(acknowledge_use_case, vault_event_repository, time_gateway):
    def _acknowledge(index: int) -> None:
        acknowledge_use_case.execute(
            AcknowledgeShareLinkCommand(lookup_hash=lookup(f"token-{index}"), ack_key=ack_key(f"token-{index}"))
        )
        _on_gateway_clock(vault_event_repository, time_gateway)

    return _acknowledge


def test_given_untouched_links_should_list_every_share_as_pending(use_case, setup, time_gateway):
    overview = _overview(use_case)

    assert (overview.setup_id, overview.nb_shares, overview.threshold) == (SETUP_ID, 3, 2)
    assert overview.created_at == time_gateway.get_current_time()
    assert [link.share_index for link in overview.links] == [1, 2, 3]
    assert _statuses(overview) == [ShareLinkStatus.PENDING] * 3
    assert overview.links[0].expires_at == time_gateway.get_current_time() + SHARE_LINK_LIFETIME
    assert all(link.open_count == 0 and link.first_opened_at is None for link in overview.links)
    assert overview.counts[ShareLinkStatus.PENDING] == 3
    assert sum(overview.counts.values()) == 3


def test_given_opened_link_within_its_window_should_be_opened(use_case, setup, retrieve, time_gateway):
    retrieve(1)

    link = _overview(use_case).links[0]

    assert link.status == ShareLinkStatus.OPENED
    assert link.first_opened_at == time_gateway.get_current_time()
    assert link.reopenable_until == time_gateway.get_current_time() + SHARE_LINK_REOPEN_WINDOW
    assert link.acknowledged_at is None


def test_given_opened_link_past_its_window_but_not_purged_should_be_opened_unconfirmed(
    use_case, setup, retrieve, time_gateway
):
    retrieve(1)
    time_gateway.set_current_time(time_gateway.get_current_time() + SHARE_LINK_REOPEN_WINDOW)

    assert _overview(use_case).links[0].status == ShareLinkStatus.OPENED_UNCONFIRMED


def test_given_opened_link_purged_should_stay_opened_unconfirmed_from_the_audit_trail(
    use_case, setup, retrieve, share_link_repository, time_gateway
):
    retrieve(1)
    opened_at = time_gateway.get_current_time()
    time_gateway.set_current_time(opened_at + SHARE_LINK_REOPEN_WINDOW)
    share_link_repository.purge_expired(time_gateway.get_current_time())

    link = _overview(use_case).links[0]

    assert link.status == ShareLinkStatus.OPENED_UNCONFIRMED
    assert link.first_opened_at == opened_at
    assert link.reopenable_until is None
    assert link.open_count == 1


def test_given_acknowledged_link_should_be_acknowledged_though_its_row_is_gone(
    use_case, setup, retrieve, acknowledge, share_link_repository, time_gateway
):
    retrieve(2)
    acknowledge(2)
    assert [link.share_index for link in share_link_repository.stored()] == [1, 3]

    link = _overview(use_case).links[1]

    assert link.status == ShareLinkStatus.ACKNOWLEDGED
    assert link.acknowledged_at == time_gateway.get_current_time()
    assert link.reopenable_until is None


def test_given_expired_link_not_yet_purged_should_be_expired(use_case, setup, time_gateway):
    time_gateway.set_current_time(time_gateway.get_current_time() + SHARE_LINK_LIFETIME)

    overview = _overview(use_case)

    assert _statuses(overview) == [ShareLinkStatus.EXPIRED] * 3
    assert overview.counts[ShareLinkStatus.EXPIRED] == 3


def test_given_never_opened_link_purged_should_be_expired_with_expiry_from_the_creation_event(
    use_case, setup, share_link_repository, time_gateway
):
    created = time_gateway.get_current_time()
    time_gateway.set_current_time(created + SHARE_LINK_LIFETIME + timedelta(hours=1))
    share_link_repository.purge_expired(time_gateway.get_current_time())

    link = _overview(use_case).links[0]

    assert link.status == ShareLinkStatus.EXPIRED
    assert link.expires_at == created + SHARE_LINK_LIFETIME
    assert link.first_opened_at is None


def test_given_link_opened_just_before_expiry_should_be_unconfirmed_not_expired(
    use_case, setup, retrieve, time_gateway
):
    created = time_gateway.get_current_time()
    time_gateway.set_current_time(created + SHARE_LINK_LIFETIME - timedelta(minutes=5))
    retrieve(1)
    time_gateway.set_current_time(created + SHARE_LINK_LIFETIME)

    assert _overview(use_case).links[0].status == ShareLinkStatus.OPENED_UNCONFIRMED


def test_given_missing_link_and_no_creation_event_should_leave_expiry_unknown(
    use_case, setup, share_link_repository, vault_event_repository, time_gateway
):
    vault_event_repository.events.clear()
    time_gateway.set_current_time(time_gateway.get_current_time() + SHARE_LINK_LIFETIME)
    share_link_repository.purge_expired(time_gateway.get_current_time())

    overview = _overview(use_case)

    assert overview.created_at is None
    assert overview.links[0].expires_at is None
    assert overview.links[0].status == ShareLinkStatus.EXPIRED


def test_given_two_openings_then_acknowledgement_should_count_and_date_them(
    use_case, setup, retrieve, acknowledge, time_gateway
):
    first = time_gateway.get_current_time() + timedelta(hours=1)
    time_gateway.set_current_time(first)
    retrieve(1)
    time_gateway.set_current_time(first + timedelta(minutes=5))
    retrieve(1)
    acked = first + timedelta(minutes=8)
    time_gateway.set_current_time(acked)
    acknowledge(1)

    link = _overview(use_case).links[0]

    assert link.status == ShareLinkStatus.ACKNOWLEDGED
    assert link.open_count == 2
    assert link.first_opened_at == first
    assert link.acknowledged_at == acked


def test_given_mixed_states_should_count_each_status(use_case, setup, retrieve, acknowledge):
    retrieve(1)
    acknowledge(1)
    retrieve(2)

    overview = _overview(use_case)

    assert _statuses(overview) == [ShareLinkStatus.ACKNOWLEDGED, ShareLinkStatus.OPENED, ShareLinkStatus.PENDING]
    assert overview.counts[ShareLinkStatus.ACKNOWLEDGED] == 1
    assert overview.counts[ShareLinkStatus.OPENED] == 1
    assert overview.counts[ShareLinkStatus.PENDING] == 1
    assert overview.counts[ShareLinkStatus.EXPIRED] == overview.counts[ShareLinkStatus.OPENED_UNCONFIRMED] == 0


def test_given_events_of_an_abandoned_setup_should_ignore_them(use_case, setup, vault_event_repository, time_gateway):
    now = time_gateway.get_current_time()
    vault_event_repository.events.append(_created_event("abandoned-setup", now - timedelta(days=3)))
    for event_type, extra in [
        ("VaultShareLinkRetrievedEvent", {"reopened": False}),
        ("VaultShareLinkRetrievedEvent", {"reopened": True}),
        ("VaultShareLinkAcknowledgedEvent", {}),
    ]:
        vault_event_repository.events.append(
            {
                "event_id": UUID(int=2),
                "event_type": event_type,
                "occurred_on": now - timedelta(days=3),
                "actor_user_id": None,
                "event_data": {"setup_id": "abandoned-setup", "share_index": 1, **extra},
            }
        )

    overview = _overview(use_case)

    assert overview.created_at == now
    assert _statuses(overview) == [ShareLinkStatus.PENDING] * 3
    assert overview.links[0].open_count == 0
    assert overview.links[0].acknowledged_at is None


def test_given_non_admin_when_viewing_should_raise_not_admin_error(use_case, setup):
    with pytest.raises(NotAdminError):
        use_case.execute(GetShareLinksOverviewCommand(requesting_user=USER))


def test_given_no_vault_when_viewing_should_raise_vault_not_setup(use_case):
    with pytest.raises(VaultNotSetupException):
        _overview(use_case)


def test_viewing_should_write_nothing_and_emit_no_event(
    use_case, setup, retrieve, share_link_repository, vault_event_repository, event_publisher
):
    retrieve(1)
    links_before = share_link_repository.stored()
    events_before = list(vault_event_repository.events)
    published_before = list(event_publisher.published_events)

    _overview(use_case)
    _overview(use_case)

    assert share_link_repository.stored() == links_before
    assert vault_event_repository.events == events_before
    assert event_publisher.published_events == published_before
