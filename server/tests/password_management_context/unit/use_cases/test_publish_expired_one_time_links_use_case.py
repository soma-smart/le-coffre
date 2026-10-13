from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from password_management_context.application.use_cases import PublishExpiredOneTimeLinksUseCase
from password_management_context.domain.entities import OneTimeLink, Password
from password_management_context.domain.events import OneTimeLinkExpiredEvent
from password_management_context.domain.value_objects import OneTimeLinkLifetime, OneTimeLinkToken
from tests.shared_kernel.fakes import FakeTimeGateway

from ..fakes import FakeOneTimeLinkRepository, FakePasswordRepository

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
CREATOR_ID = UUID("00000000-0000-0000-0000-0000000000a1")
PASSWORD_ID = UUID("00000000-0000-0000-0000-0000000000c1")
SHORTEST = OneTimeLinkLifetime(seconds=300)
AFTER_EXPIRY = T0 + timedelta(seconds=301)


@pytest.fixture
def time_gateway():
    return FakeTimeGateway(fixed_time=T0)


@pytest.fixture
def password(password_repository: FakePasswordRepository) -> Password:
    password = Password.create(id=PASSWORD_ID, name="Production database", encrypted_value="enc", login=None, url=None)
    password_repository.save(password)
    return password


def _link(
    repository: FakeOneTimeLinkRepository,
    notify_on_expiry: bool = True,
    password_id: UUID = PASSWORD_ID,
) -> OneTimeLink:
    link = OneTimeLink.create(
        password_id=password_id,
        created_by_user_id=CREATOR_ID,
        token=OneTimeLinkToken.generate(),
        lifetime=SHORTEST,
        now=T0,
        notify_on_expiry=notify_on_expiry,
    )
    repository.add(link)
    return link


@pytest.fixture
def use_case(one_time_link_repository, password_repository, domain_event_publisher, time_gateway):
    return PublishExpiredOneTimeLinksUseCase(
        one_time_link_repository, password_repository, domain_event_publisher, time_gateway
    )


def test_given_an_expired_unread_link_opted_in_when_sweeping_should_publish_exactly_one_event(
    use_case, one_time_link_repository, domain_event_publisher, time_gateway, password
):
    link = _link(one_time_link_repository)
    time_gateway.set_current_time(AFTER_EXPIRY)

    published = use_case.execute()

    assert published == 1
    (event,) = domain_event_publisher.get_published_events_of_type(OneTimeLinkExpiredEvent)
    assert event.link_id == link.id
    assert event.password_id == PASSWORD_ID
    assert event.created_by_user_id == CREATOR_ID
    assert event.password_name == "Production database"
    assert event.expires_at == link.expires_at
    assert one_time_link_repository.storage[link.id].expiry_notified_at == AFTER_EXPIRY


def test_given_a_second_sweep_should_publish_nothing(
    use_case, one_time_link_repository, domain_event_publisher, time_gateway, password
):
    _link(one_time_link_repository)
    time_gateway.set_current_time(AFTER_EXPIRY)
    use_case.execute()
    domain_event_publisher.clear_events()

    published = use_case.execute()

    assert published == 0
    assert domain_event_publisher.published_events == []


def _read(link: OneTimeLink, repository: FakeOneTimeLinkRepository) -> None:
    repository.consume(link.id, T0)


def _revoked(link: OneTimeLink, repository: FakeOneTimeLinkRepository) -> None:
    repository.revoke(link.id, T0)


@pytest.mark.parametrize("make_ineligible", [_read, _revoked], ids=["read", "revoked"])
def test_given_a_read_or_revoked_link_when_sweeping_should_publish_nothing(
    make_ineligible, use_case, one_time_link_repository, domain_event_publisher, time_gateway, password
):
    link = _link(one_time_link_repository)
    make_ineligible(link, one_time_link_repository)
    time_gateway.set_current_time(AFTER_EXPIRY)

    assert use_case.execute() == 0
    assert domain_event_publisher.published_events == []


def test_given_a_link_not_yet_expired_when_sweeping_should_publish_nothing(
    use_case, one_time_link_repository, domain_event_publisher, time_gateway, password
):
    _link(one_time_link_repository)
    time_gateway.set_current_time(T0 + timedelta(seconds=299))

    assert use_case.execute() == 0
    assert domain_event_publisher.published_events == []


def test_given_a_link_without_notify_on_expiry_when_sweeping_should_publish_nothing(
    use_case, one_time_link_repository, domain_event_publisher, time_gateway, password
):
    _link(one_time_link_repository, notify_on_expiry=False)
    time_gateway.set_current_time(AFTER_EXPIRY)

    assert use_case.execute() == 0
    assert domain_event_publisher.published_events == []


def test_given_a_deleted_password_when_sweeping_should_publish_nothing_and_not_retry_the_link(
    use_case, one_time_link_repository, domain_event_publisher, time_gateway
):
    link = _link(one_time_link_repository, password_id=uuid4())
    time_gateway.set_current_time(AFTER_EXPIRY)

    assert use_case.execute() == 0
    assert domain_event_publisher.published_events == []
    # Claimed anyway, so that it cannot clog the front of every future batch.
    assert one_time_link_repository.storage[link.id].expiry_notified_at == AFTER_EXPIRY


def test_given_a_link_claimed_by_another_replica_when_sweeping_should_publish_nothing(
    one_time_link_repository, password_repository, domain_event_publisher, time_gateway, password
):
    class LosingTheRace(FakeOneTimeLinkRepository):
        def claim_expiry_notification(self, link_id, now):
            return False

    repository = LosingTheRace()
    _link(repository)
    time_gateway.set_current_time(AFTER_EXPIRY)

    published = PublishExpiredOneTimeLinksUseCase(
        repository, password_repository, domain_event_publisher, time_gateway
    ).execute()

    assert published == 0
    assert domain_event_publisher.published_events == []


def test_given_more_expired_links_than_the_batch_when_sweeping_should_handle_one_batch_per_pass(
    one_time_link_repository, password_repository, domain_event_publisher, time_gateway, password
):
    for _ in range(5):
        _link(one_time_link_repository)
    time_gateway.set_current_time(AFTER_EXPIRY)
    use_case = PublishExpiredOneTimeLinksUseCase(
        one_time_link_repository, password_repository, domain_event_publisher, time_gateway, batch_size=2
    )

    assert [use_case.execute() for _ in range(4)] == [2, 2, 1, 0]
    assert len(domain_event_publisher.get_published_events_of_type(OneTimeLinkExpiredEvent)) == 5
