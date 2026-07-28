from datetime import UTC, datetime, timedelta, timezone

import pytest

from password_management_context.domain.exceptions import ShareExpirationInPastError
from password_management_context.domain.value_objects import (
    PasswordGroupAccess,
    PasswordPermission,
    ShareExpiration,
)

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


# ── ShareExpiration ───────────────────────────────────────────────────


def test_should_accept_an_expiration_in_the_future():
    expiration = ShareExpiration.create(T0 + timedelta(hours=1), now=T0)

    assert expiration.value == T0 + timedelta(hours=1)


def test_should_accept_an_expiration_years_away():
    """No upper bound: permanent sharing is already unbounded, so a cap would
    only push a long engagement towards never-expiring access."""
    far = T0 + timedelta(days=365 * 5)

    assert ShareExpiration.create(far, now=T0).value == far


def test_should_reject_an_expiration_in_the_past():
    with pytest.raises(ShareExpirationInPastError):
        ShareExpiration.create(T0 - timedelta(seconds=1), now=T0)


def test_should_reject_an_expiration_exactly_now():
    with pytest.raises(ShareExpirationInPastError):
        ShareExpiration.create(T0, now=T0)


def test_should_normalise_a_naive_expiration_to_utc():
    naive = datetime(2026, 1, 1, 13, 0, 0)

    assert ShareExpiration.create(naive, now=T0).value == datetime(2026, 1, 1, 13, 0, 0, tzinfo=UTC)


def test_should_compare_across_timezones():
    """An aware datetime in another zone must be judged on its instant, not its wall clock."""
    tehran = datetime(2026, 1, 1, 12, 30, 0, tzinfo=UTC).astimezone(timezone(timedelta(hours=3, minutes=30)))

    assert ShareExpiration.create(tehran, now=T0).value == datetime(2026, 1, 1, 12, 30, 0, tzinfo=UTC)


# ── PasswordGroupAccess ───────────────────────────────────────────────


def _shared(expires_at: datetime | None) -> PasswordGroupAccess:
    return PasswordGroupAccess(is_owner=False, permissions={PasswordPermission.READ}, expires_at=expires_at)


def test_a_permanent_share_never_expires():
    access = _shared(None)

    assert not access.is_expired(T0 + timedelta(days=3650))
    assert access.grants_read(T0)


def test_a_temporary_share_grants_read_before_its_expiry():
    access = _shared(T0 + timedelta(hours=1))

    assert access.grants_read(T0)
    assert not access.is_expired(T0)


def test_a_temporary_share_stops_granting_read_at_its_expiry():
    access = _shared(T0)

    assert access.is_expired(T0)
    assert not access.grants_read(T0)


def test_an_owner_never_expires():
    """Ownership lives in its own table and carries no expiry, so it cannot be timed out."""
    owner = PasswordGroupAccess(is_owner=True, permissions=set(), expires_at=None)

    assert owner.grants_read(T0 + timedelta(days=3650))
    assert not owner.is_expired(T0 + timedelta(days=3650))


def test_a_share_without_read_permission_grants_nothing():
    access = PasswordGroupAccess(is_owner=False, permissions=set(), expires_at=None)

    assert not access.grants_read(T0)


def test_should_default_to_a_permanent_share():
    assert PasswordGroupAccess(is_owner=False, permissions={PasswordPermission.READ}).expires_at is None
