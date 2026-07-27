from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from password_management_context.domain.entities import OneTimeLink
from password_management_context.domain.exceptions import (
    InvalidOneTimeLinkTokenError,
    OneTimeLinkAlreadyUsedError,
    OneTimeLinkExpiredError,
    OneTimeLinkLifetimeTooLongError,
    OneTimeLinkLifetimeTooShortError,
    OneTimeLinkRevokedError,
)
from password_management_context.domain.value_objects import (
    OneTimeLinkLifetime,
    OneTimeLinkToken,
)
from password_management_context.domain.value_objects.one_time_link_lifetime import (
    DEFAULT_LIFETIME_SECONDS,
    MAX_LIFETIME_SECONDS,
    MIN_LIFETIME_SECONDS,
)

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _build_link(now: datetime = T0, lifetime: OneTimeLinkLifetime | None = None) -> OneTimeLink:
    return OneTimeLink.create(
        password_id=uuid4(),
        created_by_user_id=uuid4(),
        token=OneTimeLinkToken.generate(),
        lifetime=lifetime or OneTimeLinkLifetime.default(),
        now=now,
    )


# ── OneTimeLinkLifetime ───────────────────────────────────────────────


def test_should_default_to_one_day():
    assert OneTimeLinkLifetime.default().seconds == DEFAULT_LIFETIME_SECONDS
    assert OneTimeLinkLifetime.default().as_timedelta() == timedelta(days=1)


def test_should_accept_the_exact_boundaries():
    assert OneTimeLinkLifetime(seconds=MIN_LIFETIME_SECONDS).seconds == MIN_LIFETIME_SECONDS
    assert OneTimeLinkLifetime(seconds=MAX_LIFETIME_SECONDS).seconds == MAX_LIFETIME_SECONDS


def test_should_reject_a_lifetime_below_the_minimum():
    with pytest.raises(OneTimeLinkLifetimeTooShortError):
        OneTimeLinkLifetime(seconds=MIN_LIFETIME_SECONDS - 1)


def test_should_reject_a_lifetime_above_the_maximum():
    with pytest.raises(OneTimeLinkLifetimeTooLongError):
        OneTimeLinkLifetime(seconds=MAX_LIFETIME_SECONDS + 1)


# ── OneTimeLinkToken ──────────────────────────────────────────────────


def test_should_generate_distinct_tokens():
    assert OneTimeLinkToken.generate().value != OneTimeLinkToken.generate().value


def test_should_never_leak_the_token_in_its_representation():
    token = OneTimeLinkToken.generate()

    assert token.value not in repr(token)
    assert token.value not in str(token)


def test_should_hash_deterministically_and_not_return_the_token():
    token = OneTimeLinkToken.generate()

    assert token.hashed() == OneTimeLinkToken(value=token.value).hashed()
    assert token.hashed() != token.value
    assert len(token.hashed()) == 64


def test_should_reject_a_token_too_short_to_have_been_generated():
    with pytest.raises(InvalidOneTimeLinkTokenError):
        OneTimeLinkToken(value="too-short")


# ── OneTimeLink state machine ─────────────────────────────────────────


def test_should_be_consumable_when_fresh():
    _build_link().ensure_consumable(T0)


def test_should_expire_exactly_at_its_expiry_instant():
    link = _build_link()

    assert not link.is_expired(link.expires_at - timedelta(seconds=1))
    assert link.is_expired(link.expires_at)


def test_should_raise_when_consumed_after_expiry():
    link = _build_link()

    with pytest.raises(OneTimeLinkExpiredError):
        link.ensure_consumable(link.expires_at + timedelta(seconds=1))


def test_should_raise_when_consumed_twice():
    link = _build_link()
    link.mark_read(T0)

    with pytest.raises(OneTimeLinkAlreadyUsedError):
        link.ensure_consumable(T0)


def test_should_raise_when_revoked():
    link = _build_link()
    link.mark_revoked(T0)

    with pytest.raises(OneTimeLinkRevokedError):
        link.ensure_consumable(T0)


def test_should_report_revoked_before_expired_so_the_owner_action_is_the_reason():
    """A revoked link that also expired reports revocation: the owner's
    deliberate act is the more meaningful of the two for an audit reader."""
    link = _build_link()
    link.mark_revoked(T0)

    with pytest.raises(OneTimeLinkRevokedError):
        link.ensure_consumable(link.expires_at + timedelta(days=1))
