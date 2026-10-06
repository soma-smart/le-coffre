import hashlib
from datetime import timedelta

import pytest

from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from vault_management_context.application.commands import RetrieveShareLinkCommand
from vault_management_context.application.use_cases import RetrieveShareLinkUseCase
from vault_management_context.domain.entities import ShareLink
from vault_management_context.domain.events import VaultShareLinkRetrievedEvent
from vault_management_context.domain.exceptions import (
    InvalidShareLinkLookupError,
    ShareLinkUnusableError,
)

from ..fakes import FakeShareLinkRepository

SETUP_ID = "setup-1"


def _lookup(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@pytest.fixture()
def use_case(share_link_repository, event_publisher, vault_event_repository, time_gateway):
    return RetrieveShareLinkUseCase(share_link_repository, event_publisher, vault_event_repository, time_gateway)


@pytest.fixture()
def links(share_link_repository: FakeShareLinkRepository, time_gateway) -> list[ShareLink]:
    now = time_gateway.get_current_time()
    issued = [
        ShareLink.create(
            setup_id=SETUP_ID,
            share_index=index,
            lookup_hash=_lookup(f"token-{index}"),
            sealed_share=f"sealed-{index}",
            now=now,
        )
        for index in (1, 2, 3)
    ]
    share_link_repository.replace_all(issued)
    return issued


def test_given_pending_link_when_retrieving_should_return_its_sealed_share(use_case, links):
    result = use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("token-2")))

    assert result.share_index == 2
    assert result.sealed_share == "sealed-2"


def test_given_pending_link_when_retrieving_should_delete_it_and_leave_the_others(
    use_case, links, share_link_repository: FakeShareLinkRepository
):
    use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("token-2")))

    assert share_link_repository.get_by_lookup_hash(_lookup("token-2")) is None
    assert [link.share_index for link in share_link_repository.stored()] == [1, 3]


def test_given_retrieved_link_when_retrieving_again_should_refuse(use_case, links):
    use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("token-1")))

    with pytest.raises(ShareLinkUnusableError):
        use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("token-1")))


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


def test_given_link_past_48_hours_when_retrieving_should_refuse_and_purge_expired_links(
    use_case, links, share_link_repository: FakeShareLinkRepository, time_gateway
):
    time_gateway.set_current_time(time_gateway.get_current_time() + timedelta(hours=48))

    with pytest.raises(ShareLinkUnusableError):
        use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("token-1")))

    assert share_link_repository.stored() == []


def test_given_link_just_before_expiry_when_retrieving_should_succeed(use_case, links, time_gateway):
    time_gateway.set_current_time(time_gateway.get_current_time() + timedelta(hours=48) - timedelta(seconds=1))

    result = use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("token-3")))

    assert result.sealed_share == "sealed-3"


def test_given_concurrent_retrieval_won_elsewhere_when_retrieving_should_refuse_and_not_audit(
    use_case,
    links,
    share_link_repository: FakeShareLinkRepository,
    event_publisher: FakeDomainEventPublisher,
    vault_event_repository,
):
    share_link_repository.lose_next_retrieval_race()

    with pytest.raises(ShareLinkUnusableError):
        use_case.execute(RetrieveShareLinkCommand(lookup_hash=_lookup("token-1")))

    assert event_publisher.get_published_events_of_type(VaultShareLinkRetrievedEvent) == []
    assert vault_event_repository.events == []


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
    assert stored["event_data"] == {"setup_id": SETUP_ID, "share_index": 3}
