from datetime import timedelta

import pytest

from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from tests.shared_kernel.fakes import FakeTransactionGateway
from vault_management_context.application.commands import AcknowledgeShareLinkCommand, RetrieveShareLinkCommand
from vault_management_context.application.use_cases import AcknowledgeShareLinkUseCase, RetrieveShareLinkUseCase
from vault_management_context.domain.entities import SHARE_LINK_LIFETIME, SHARE_LINK_REOPEN_WINDOW
from vault_management_context.domain.events import VaultShareLinkAcknowledgedEvent
from vault_management_context.domain.exceptions import (
    InvalidShareLinkLookupError,
    ShareLinkAckRejectedError,
    ShareLinkUnusableError,
)

from ..fakes import FakeShareLinkRepository, FakeVaultEventRepository
from ..share_links import SETUP_ID, ack_key, issue_links, lookup


@pytest.fixture()
def use_case(share_link_repository, event_publisher, vault_event_repository, time_gateway, transaction_gateway):
    return AcknowledgeShareLinkUseCase(
        share_link_repository, event_publisher, vault_event_repository, time_gateway, transaction_gateway
    )


@pytest.fixture()
def links(share_link_repository: FakeShareLinkRepository, time_gateway):
    return issue_links(share_link_repository, time_gateway.get_current_time())


@pytest.fixture()
def retrieve(share_link_repository, event_publisher, vault_event_repository, time_gateway, transaction_gateway):
    use_case = RetrieveShareLinkUseCase(
        share_link_repository, event_publisher, vault_event_repository, time_gateway, transaction_gateway
    )
    return lambda token: use_case.execute(RetrieveShareLinkCommand(lookup_hash=lookup(token)))


def _ack(use_case, token: str, key: str | None = None) -> None:
    use_case.execute(AcknowledgeShareLinkCommand(lookup_hash=lookup(token), ack_key=key or ack_key(token)))


def test_given_retrieved_link_when_acknowledging_should_delete_it_and_leave_the_others(
    use_case, links, retrieve, share_link_repository: FakeShareLinkRepository
):
    retrieve("token-2")

    _ack(use_case, "token-2")

    assert [link.share_index for link in share_link_repository.stored()] == [1, 3]


def test_given_acknowledged_link_when_retrieving_again_should_refuse(use_case, links, retrieve):
    retrieve("token-2")
    _ack(use_case, "token-2")

    with pytest.raises(ShareLinkUnusableError):
        retrieve("token-2")


def test_given_link_never_retrieved_when_acknowledging_should_refuse_and_keep_it(
    use_case, links, share_link_repository: FakeShareLinkRepository
):
    with pytest.raises(ShareLinkUnusableError):
        _ack(use_case, "token-1")

    assert len(share_link_repository.stored()) == 3


def test_given_ack_key_of_another_link_when_acknowledging_should_reject_and_keep_it(
    use_case, links, retrieve, share_link_repository: FakeShareLinkRepository
):
    retrieve("token-1")

    with pytest.raises(ShareLinkAckRejectedError):
        _ack(use_case, "token-1", key=ack_key("token-2"))

    assert len(share_link_repository.stored()) == 3


def test_given_only_the_lookup_hash_when_acknowledging_should_reject(use_case, links, retrieve):
    # The database holds the lookup hash; it must not be enough to close a link.
    retrieve("token-1")

    with pytest.raises(ShareLinkAckRejectedError):
        _ack(use_case, "token-1", key=lookup("token-1"))


@pytest.mark.parametrize("key", ["", "abc", "Z" * 64, "A" * 64])
def test_given_malformed_ack_key_when_acknowledging_should_reject_before_any_lookup(use_case, links, key):
    with pytest.raises(ShareLinkAckRejectedError):
        use_case.execute(AcknowledgeShareLinkCommand(lookup_hash=lookup("token-1"), ack_key=key))


def test_given_malformed_lookup_hash_when_acknowledging_should_reject_it(use_case, links):
    with pytest.raises(InvalidShareLinkLookupError):
        use_case.execute(AcknowledgeShareLinkCommand(lookup_hash="token-1", ack_key=ack_key("token-1")))


def test_given_unknown_link_when_acknowledging_should_refuse(use_case, links):
    with pytest.raises(ShareLinkUnusableError):
        _ack(use_case, "never-issued")


def test_given_concurrent_ack_won_elsewhere_when_acknowledging_should_refuse_and_not_audit(
    use_case,
    links,
    retrieve,
    share_link_repository: FakeShareLinkRepository,
    vault_event_repository: FakeVaultEventRepository,
):
    retrieve("token-1")
    audited_before = len(vault_event_repository.events)
    share_link_repository.lose_next_removal_race()

    with pytest.raises(ShareLinkUnusableError):
        _ack(use_case, "token-1")

    assert len(vault_event_repository.events) == audited_before


def test_given_retrieved_link_when_acknowledging_should_publish_and_store_an_anonymous_audit_event(
    use_case,
    links,
    retrieve,
    event_publisher: FakeDomainEventPublisher,
    vault_event_repository: FakeVaultEventRepository,
    transaction_gateway: FakeTransactionGateway,
):
    retrieve("token-3")

    _ack(use_case, "token-3")

    events = event_publisher.get_published_events_of_type(VaultShareLinkAcknowledgedEvent)
    assert [(event.setup_id, event.share_index) for event in events] == [(SETUP_ID, 3)]
    stored = vault_event_repository.events[-1]
    assert stored["event_type"] == "VaultShareLinkAcknowledgedEvent"
    assert stored["actor_user_id"] is None
    assert stored["event_data"] == {"setup_id": SETUP_ID, "share_index": 3}
    # One transaction for the retrieval, one for the acknowledgement
    assert transaction_gateway.committed == 2


def test_given_audit_write_fails_when_acknowledging_should_roll_back_and_publish_nothing(
    use_case,
    links,
    retrieve,
    vault_event_repository: FakeVaultEventRepository,
    transaction_gateway: FakeTransactionGateway,
    event_publisher: FakeDomainEventPublisher,
):
    retrieve("token-2")
    vault_event_repository.error = RuntimeError("audit write failed")

    with pytest.raises(RuntimeError):
        _ack(use_case, "token-2")

    assert transaction_gateway.rolled_back == 1
    assert event_publisher.get_published_events_of_type(VaultShareLinkAcknowledgedEvent) == []


@pytest.mark.parametrize(
    "after_first_opening",
    [SHARE_LINK_REOPEN_WINDOW, SHARE_LINK_REOPEN_WINDOW + timedelta(hours=1)],
    ids=["window just over", "awaiting the purge"],
)
def test_given_link_past_its_reopen_window_when_acknowledging_should_refuse_and_not_audit(
    use_case,
    links,
    retrieve,
    time_gateway,
    share_link_repository: FakeShareLinkRepository,
    vault_event_repository: FakeVaultEventRepository,
    after_first_opening,
):
    # Closed on its own: the audit trail must not show the custodian closing it.
    retrieve("token-1")
    audited_before = len(vault_event_repository.events)
    time_gateway.set_current_time(time_gateway.get_current_time() + after_first_opening)

    with pytest.raises(ShareLinkUnusableError):
        _ack(use_case, "token-1")

    assert len(vault_event_repository.events) == audited_before
    assert len(share_link_repository.stored()) == 3


def test_given_expired_link_when_acknowledging_should_refuse(use_case, links, retrieve, time_gateway):
    issued_at = time_gateway.get_current_time()
    time_gateway.set_current_time(issued_at + SHARE_LINK_LIFETIME - timedelta(minutes=5))
    retrieve("token-1")
    time_gateway.set_current_time(issued_at + SHARE_LINK_LIFETIME)

    with pytest.raises(ShareLinkUnusableError):
        _ack(use_case, "token-1")
