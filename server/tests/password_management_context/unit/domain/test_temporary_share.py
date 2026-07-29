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


# These four rules are proved through GetPasswordUseCase with a fake clock in
# test_temporary_share_use_cases.py, so they are not restated here: a permanent
# share never expiring, read granted before the deadline, read lost at it, and
# the owner outliving the recipient's share.


def test_a_share_without_read_permission_grants_nothing():
    access = PasswordGroupAccess(is_owner=False, permissions=set(), expires_at=None)

    assert not access.grants_read(T0)


def test_should_default_to_a_permanent_share():
    assert PasswordGroupAccess(is_owner=False, permissions={PasswordPermission.READ}).expires_at is None
