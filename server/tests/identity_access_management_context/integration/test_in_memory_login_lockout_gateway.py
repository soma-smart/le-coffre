from datetime import UTC, datetime, timedelta

import pytest

from identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway import (
    InMemoryLoginLockoutGateway,
)

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def gateway() -> InMemoryLoginLockoutGateway:
    return InMemoryLoginLockoutGateway(max_failures=3, lockout_seconds=60)


def test_given_email_with_no_recorded_failures_when_checking_should_return_none(
    gateway: InMemoryLoginLockoutGateway,
):
    assert gateway.is_locked("unknown@lecoffre.com", T0) is None


def test_given_failures_below_threshold_when_checking_should_not_lock(gateway: InMemoryLoginLockoutGateway):
    for _ in range(2):
        gateway.record_failed_login("alice@lecoffre.com", T0)

    assert gateway.is_locked("alice@lecoffre.com", T0) is None


def test_given_failure_count_reaches_threshold_when_checking_should_lock(
    gateway: InMemoryLoginLockoutGateway,
):
    for _ in range(3):
        gateway.record_failed_login("alice@lecoffre.com", T0)

    assert gateway.is_locked("alice@lecoffre.com", T0) == 60


def test_given_account_locked_when_checking_mid_window_should_return_remaining_seconds(
    gateway: InMemoryLoginLockoutGateway,
):
    for _ in range(3):
        gateway.record_failed_login("alice@lecoffre.com", T0)

    assert gateway.is_locked("alice@lecoffre.com", T0 + timedelta(seconds=45)) == 15


def test_given_lockout_duration_elapsed_when_checking_should_return_none(
    gateway: InMemoryLoginLockoutGateway,
):
    for _ in range(3):
        gateway.record_failed_login("alice@lecoffre.com", T0)

    assert gateway.is_locked("alice@lecoffre.com", T0 + timedelta(seconds=61)) is None


def test_given_expired_lockout_when_recording_failure_should_start_fresh_sequence(
    gateway: InMemoryLoginLockoutGateway,
):
    for _ in range(3):
        gateway.record_failed_login("alice@lecoffre.com", T0)

    gateway.record_failed_login("alice@lecoffre.com", T0 + timedelta(seconds=61))

    assert gateway.is_locked("alice@lecoffre.com", T0 + timedelta(seconds=61)) is None


def test_given_active_lockout_when_recording_more_failures_should_not_extend_the_window(
    gateway: InMemoryLoginLockoutGateway,
):
    """The use case gates on is_locked before calling record_failed_login, but
    the Protocol makes no such guarantee — a misbehaving caller that records
    failures during an active lockout must NOT extend the window. Otherwise
    repeated misuse silently turns a 60s lock into an indefinite one."""
    for _ in range(3):
        gateway.record_failed_login("alice@lecoffre.com", T0)

    # Baseline: locked until T0+60. At T0+10 there should be 50 seconds left.
    assert gateway.is_locked("alice@lecoffre.com", T0 + timedelta(seconds=10)) == 50

    # Caller-contract violation: record max_failures more failures during the
    # active lockout. A naive impl would re-arm the lock at T0+10+60=T0+70,
    # extending the original T0+60 window by 10 seconds.
    for offset in (10, 11, 12):
        gateway.record_failed_login("alice@lecoffre.com", T0 + timedelta(seconds=offset))

    # The lock must still expire at the ORIGINAL T0+60. At T0+12 the remaining
    # window is 48 seconds, not 58 (which would be the extended-lock result).
    assert gateway.is_locked("alice@lecoffre.com", T0 + timedelta(seconds=12)) == 48, (
        "Recording failures during an active lockout extended the window — "
        "repeated calls would silently turn a fixed-duration lock into an open-ended one"
    )
    # And the lock releases at the original time.
    assert gateway.is_locked("alice@lecoffre.com", T0 + timedelta(seconds=61)) is None


def test_given_successful_login_recorded_when_checking_should_clear_failure_state(
    gateway: InMemoryLoginLockoutGateway,
):
    for _ in range(2):
        gateway.record_failed_login("alice@lecoffre.com", T0)

    gateway.record_successful_login("alice@lecoffre.com")

    for _ in range(2):
        gateway.record_failed_login("alice@lecoffre.com", T0)

    assert gateway.is_locked("alice@lecoffre.com", T0) is None


def test_given_one_email_fails_when_checking_another_should_not_be_affected(
    gateway: InMemoryLoginLockoutGateway,
):
    for _ in range(3):
        gateway.record_failed_login("alice@lecoffre.com", T0)

    assert gateway.is_locked("bob@lecoffre.com", T0) is None


def test_given_max_failures_is_zero_when_instantiating_should_raise_value_error():
    with pytest.raises(ValueError, match="max_failures"):
        InMemoryLoginLockoutGateway(max_failures=0, lockout_seconds=60)


def test_given_lockout_seconds_is_zero_when_instantiating_should_raise_value_error():
    with pytest.raises(ValueError, match="lockout_seconds"):
        InMemoryLoginLockoutGateway(max_failures=3, lockout_seconds=0)
