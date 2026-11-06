from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from notification_context.application.commands import SubscribeToOneTimeLinkCommand
from notification_context.application.use_cases import SubscribeToOneTimeLinkUseCase
from notification_context.domain.entities import OneTimeLinkSubscription
from notification_context.domain.exceptions import OneTimeLinkNoLongerActiveError, OneTimeLinkNotFoundError
from notification_context.domain.value_objects import OneTimeLinkDetails
from tests.shared_kernel.fakes import FakeTimeGateway

from ..fakes import FakeOneTimeLinkGateway, FakeOneTimeLinkSubscriptionRepository

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
CREATOR_ID = UUID("00000000-0000-0000-0000-0000000000a1")
OTHER_USER_ID = UUID("00000000-0000-0000-0000-0000000000a2")
LINK_ID = UUID("00000000-0000-0000-0000-0000000000b1")
EXPIRES_AT = T0 + timedelta(hours=1)


def _link(**overrides) -> OneTimeLinkDetails:
    fields = dict(
        link_id=LINK_ID,
        created_by_user_id=CREATOR_ID,
        password_name="Prod DB",
        expires_at=EXPIRES_AT,
        read_at=None,
        revoked_at=None,
    )
    fields.update(overrides)
    return OneTimeLinkDetails(**fields)  # type: ignore[arg-type]


def _command(user_id: UUID = CREATOR_ID, notify_on_read: bool = True, notify_on_expiry: bool = False):
    return SubscribeToOneTimeLinkCommand(
        link_id=LINK_ID, user_id=user_id, notify_on_read=notify_on_read, notify_on_expiry=notify_on_expiry
    )


@pytest.fixture
def time_gateway():
    return FakeTimeGateway(fixed_time=T0)


@pytest.fixture
def use_case(
    subscription_repository: FakeOneTimeLinkSubscriptionRepository,
    one_time_link_gateway: FakeOneTimeLinkGateway,
    time_gateway: FakeTimeGateway,
):
    return SubscribeToOneTimeLinkUseCase(subscription_repository, one_time_link_gateway, time_gateway)


def test_given_the_creator_of_an_active_link_should_store_the_subscription_with_the_link_expiry(
    use_case, one_time_link_gateway, subscription_repository
):
    one_time_link_gateway.add(_link())

    result = use_case.execute(_command(notify_on_read=True, notify_on_expiry=True))

    expected = OneTimeLinkSubscription(
        link_id=LINK_ID, user_id=CREATOR_ID, expires_at=EXPIRES_AT, notify_on_read=True, notify_on_expiry=True
    )
    assert result == expected
    assert subscription_repository.get(LINK_ID) == expected


def test_given_an_existing_subscription_should_replace_it(use_case, one_time_link_gateway, subscription_repository):
    one_time_link_gateway.add(_link())
    use_case.execute(_command(notify_on_read=True, notify_on_expiry=False))

    use_case.execute(_command(notify_on_read=False, notify_on_expiry=True))

    stored = subscription_repository.get(LINK_ID)
    assert stored is not None
    assert (stored.notify_on_read, stored.notify_on_expiry) == (False, True)


def test_given_both_options_off_should_remove_the_subscription(
    use_case, one_time_link_gateway, subscription_repository
):
    one_time_link_gateway.add(_link())
    use_case.execute(_command(notify_on_read=True))

    use_case.execute(_command(notify_on_read=False, notify_on_expiry=False))

    assert subscription_repository.get(LINK_ID) is None


def test_given_an_unknown_link_should_raise_not_found(use_case, subscription_repository):
    with pytest.raises(OneTimeLinkNotFoundError):
        use_case.execute(_command())

    assert subscription_repository.get(LINK_ID) is None


def test_given_a_link_created_by_someone_else_should_raise_not_found(
    use_case, one_time_link_gateway, subscription_repository
):
    one_time_link_gateway.add(_link())

    with pytest.raises(OneTimeLinkNotFoundError):
        use_case.execute(_command(user_id=OTHER_USER_ID))

    assert subscription_repository.get(LINK_ID) is None


@pytest.mark.parametrize(
    "link",
    [
        _link(read_at=T0 - timedelta(minutes=1)),
        _link(revoked_at=T0 - timedelta(minutes=1)),
        _link(expires_at=T0),
    ],
    ids=["read", "revoked", "expired"],
)
def test_given_a_link_that_can_no_longer_be_read_should_refuse_to_follow_it(
    link, use_case, one_time_link_gateway, subscription_repository
):
    one_time_link_gateway.add(link)

    with pytest.raises(OneTimeLinkNoLongerActiveError):
        use_case.execute(_command())

    assert subscription_repository.get(LINK_ID) is None
