from datetime import timedelta

import pytest

from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from tests.shared_kernel.fakes import FakeTransactionGateway
from vault_management_context.application.commands import RetrieveShareLinkCommand
from vault_management_context.application.use_cases import RetrieveShareLinkUseCase
from vault_management_context.domain.entities import SHARE_LINK_REOPEN_WINDOW, ShareLink
from vault_management_context.domain.events import VaultShareLinkRetrievedEvent
from vault_management_context.domain.exceptions import (
    InvalidShareLinkLookupError,
    ShareLinkUnusableError,
)

from ..fakes import FakeShareLinkRepository, FakeVaultEventRepository
from ..share_links import SETUP_ID, issue_links
from ..share_links import lookup as _lookup


@pytest.fixture()
def use_case(share_link_repository, event_publisher, vault_event_repository, time_gateway, transaction_gateway):
    return RetrieveShareLinkUseCase(
        share_link_repository, event_publisher, vault_event_repository, time_gateway, transaction_gateway
    )


@pytest.fixture()
def links(share_link_repository: FakeShareLinkRepository, time_gateway) -> list[ShareLink]:
    return issue_links(share_link_repository, time_gateway.get_current_time())


def _retrieve(use_case, token: str):
    return use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup(token)))


def test_given_pending_link_when_retrieving_should_return_its_sealed_share(use_case, links):
    result = use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("token-2")))

    assert result.share_index == 2
    assert result.sealed_share == "sealed-2"


def test_given_pending_link_when_retrieving_should_keep_it_and_open_a_reopen_window(
    use_case, links, share_link_repository: FakeShareLinkRepository, time_gateway
):
    now = time_gateway.get_current_time()

    result = _retrieve(use_case, "token-2")

    # Not deleted: the share is only safe once the custodian acknowledges it
    stored = share_link_repository.get_by_lookup_hash(_lookup("token-2"))
    assert stored is not None and stored.delivered_at == now
    assert (result.first_retrieved_at, result.reopened) == (now, False)
    assert result.reopenable_until == now + SHARE_LINK_REOPEN_WINDOW


def test_given_retrieved_link_when_retrieving_again_within_the_window_should_flag_a_reopening(
    use_case, links, time_gateway
):
    first = time_gateway.get_current_time()
    _retrieve(use_case, "token-1")
    time_gateway.set_current_time(first + SHARE_LINK_REOPEN_WINDOW - timedelta(seconds=1))

    again = _retrieve(use_case, "token-1")

    assert again.sealed_share == "sealed-1"
    assert (again.first_retrieved_at, again.reopened) == (first, True)


def test_given_retrieved_link_when_its_reopen_window_is_over_should_refuse(use_case, links, time_gateway):
    _retrieve(use_case, "token-1")
    time_gateway.set_current_time(time_gateway.get_current_time() + SHARE_LINK_REOPEN_WINDOW)

    with pytest.raises(ShareLinkUnusableError):
        _retrieve(use_case, "token-1")


def test_given_unknown_link_when_retrieving_should_refuse_with_the_same_error(use_case, links):
    with pytest.raises(ShareLinkUnusableError):
        use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("never-issued")))


@pytest.mark.parametrize(
    "lookup_hash",
    ["", "abc", "Z" * 64, "A" * 64, _lookup("x") + "0", "token-1"],
)
def test_given_malformed_lookup_hash_when_retrieving_should_reject_it_before_any_lookup(use_case, links, lookup_hash):
    with pytest.raises(InvalidShareLinkLookupError):
        use_case.execute(RetrieveShareLinkCommand(lookup_hash=lookup_hash))


def test_given_link_past_48_hours_when_retrieving_should_refuse(use_case, links, time_gateway):
    time_gateway.set_current_time(time_gateway.get_current_time() + timedelta(hours=48))

    with pytest.raises(ShareLinkUnusableError):
        use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("token-1")))


def test_given_unknown_link_when_retrieving_should_write_nothing(
    use_case, links, share_link_repository: FakeShareLinkRepository, time_gateway
):
    # Anonymous endpoint: a lookup alone must not cost a write, not even the
    # purge of links that have expired in the meantime.
    time_gateway.set_current_time(time_gateway.get_current_time() + timedelta(hours=48))

    with pytest.raises(ShareLinkUnusableError):
        use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("unknown")))

    assert len(share_link_repository.stored()) == 3


def test_given_link_just_before_expiry_when_retrieving_should_succeed(use_case, links, time_gateway):
    time_gateway.set_current_time(time_gateway.get_current_time() + timedelta(hours=48) - timedelta(seconds=1))

    result = use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("token-3")))

    assert result.sealed_share == "sealed-3"


def test_given_concurrent_first_retrieval_won_elsewhere_when_retrieving_should_flag_a_reopening(
    use_case, links, share_link_repository: FakeShareLinkRepository, time_gateway
):
    other = time_gateway.get_current_time() - timedelta(seconds=1)
    share_link_repository.lose_next_first_delivery_race(other, other + SHARE_LINK_REOPEN_WINDOW)

    result = _retrieve(use_case, "token-1")

    assert (result.first_retrieved_at, result.reopened) == (other, True)


def test_given_pending_link_when_retrieving_should_publish_and_store_an_anonymous_audit_event(
    use_case, links, event_publisher: FakeDomainEventPublisher, vault_event_repository
):
    use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("token-3")))

    events = event_publisher.get_published_events_of_type(VaultShareLinkRetrievedEvent)
    assert len(events) == 1
    assert events[0].setup_id == SETUP_ID
    assert events[0].share_index == 3

    assert len(vault_event_repository.events) == 1
    stored = vault_event_repository.events[0]
    assert stored["event_type"] == "VaultShareLinkRetrievedEvent"
    assert stored["actor_user_id"] is None
    # The audit trail says which share was collected, never what it was.
    assert stored["event_data"] == {"setup_id": SETUP_ID, "share_index": 3, "reopened": False}


def test_given_reopening_when_retrieving_should_audit_it_as_such(
    use_case, links, event_publisher: FakeDomainEventPublisher, vault_event_repository
):
    _retrieve(use_case, "token-3")
    _retrieve(use_case, "token-3")

    assert [event["event_data"]["reopened"] for event in vault_event_repository.events] == [False, True]
    events = event_publisher.get_published_events_of_type(VaultShareLinkRetrievedEvent)
    assert [event.reopened for event in events] == [False, True]


def test_given_pending_link_when_retrieving_should_commit_the_delivery_and_its_audit_together(
    use_case, links, transaction_gateway: FakeTransactionGateway
):
    use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("token-2")))

    assert transaction_gateway.committed == 1
    assert transaction_gateway.rolled_back == 0


def test_given_audit_write_fails_when_retrieving_should_roll_back_and_publish_nothing(
    use_case,
    links,
    vault_event_repository: FakeVaultEventRepository,
    transaction_gateway: FakeTransactionGateway,
    event_publisher: FakeDomainEventPublisher,
):
    vault_event_repository.error = RuntimeError("audit write failed")

    with pytest.raises(RuntimeError):
        use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("token-2")))

    assert transaction_gateway.rolled_back == 1
    assert event_publisher.get_published_events_of_type(VaultShareLinkRetrievedEvent) == []


def test_given_commit_fails_when_retrieving_should_publish_nothing(
    use_case, links, transaction_gateway: FakeTransactionGateway, event_publisher: FakeDomainEventPublisher
):
    transaction_gateway.commit_error = RuntimeError("commit failed")

    with pytest.raises(RuntimeError):
        use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("token-2")))

    assert event_publisher.get_published_events_of_type(VaultShareLinkRetrievedEvent) == []


def test_given_first_opening_just_before_expiry_when_retrieving_should_end_the_window_with_the_link(
    use_case, links, time_gateway
):
    expiry = links[0].expires_at
    time_gateway.set_current_time(expiry - timedelta(minutes=5))

    result = _retrieve(use_case, "token-1")

    # The deadline shown to the custodian is never one the server will not honour
    assert result.reopenable_until == expiry
    time_gateway.set_current_time(expiry)
    with pytest.raises(ShareLinkUnusableError):
        _retrieve(use_case, "token-1")
