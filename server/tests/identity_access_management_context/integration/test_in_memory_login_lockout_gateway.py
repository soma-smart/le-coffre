from datetime import UTC, datetime, timedelta

import pytest
from identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway import (
    InMemoryLoginLockoutGateway,
)

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def gateway() -> InMemoryLoginLockoutGateway:
    return InMemoryLoginLockoutGateway(max_failures=3, lockout_seconds=60)


class TestInMemoryLoginLockoutGateway:
    def test_should_return_none_when_email_has_no_recorded_failures(self, gateway: InMemoryLoginLockoutGateway):
        assert gateway.is_locked("unknown@lecoffre.com", T0) is None

    def test_should_not_lock_when_failures_are_below_threshold(self, gateway: InMemoryLoginLockoutGateway):
        for _ in range(2):
            gateway.record_failed_login("alice@lecoffre.com", T0)

        assert gateway.is_locked("alice@lecoffre.com", T0) is None

    def test_should_lock_when_failure_count_reaches_threshold(self, gateway: InMemoryLoginLockoutGateway):
        for _ in range(3):
            gateway.record_failed_login("alice@lecoffre.com", T0)

        assert gateway.is_locked("alice@lecoffre.com", T0) == 60

    def test_should_return_remaining_seconds_when_account_currently_locked(self, gateway: InMemoryLoginLockoutGateway):
        for _ in range(3):
            gateway.record_failed_login("alice@lecoffre.com", T0)

        assert gateway.is_locked("alice@lecoffre.com", T0 + timedelta(seconds=45)) == 15

    def test_should_return_none_when_lockout_duration_has_elapsed(self, gateway: InMemoryLoginLockoutGateway):
        for _ in range(3):
            gateway.record_failed_login("alice@lecoffre.com", T0)

        assert gateway.is_locked("alice@lecoffre.com", T0 + timedelta(seconds=61)) is None

    def test_should_require_fresh_sequence_when_recording_failure_after_expired_lockout(
        self, gateway: InMemoryLoginLockoutGateway
    ):
        for _ in range(3):
            gateway.record_failed_login("alice@lecoffre.com", T0)

        gateway.record_failed_login("alice@lecoffre.com", T0 + timedelta(seconds=61))

        assert gateway.is_locked("alice@lecoffre.com", T0 + timedelta(seconds=61)) is None

    def test_should_clear_failure_state_when_successful_login_is_recorded(self, gateway: InMemoryLoginLockoutGateway):
        for _ in range(2):
            gateway.record_failed_login("alice@lecoffre.com", T0)

        gateway.record_successful_login("alice@lecoffre.com")

        for _ in range(2):
            gateway.record_failed_login("alice@lecoffre.com", T0)

        assert gateway.is_locked("alice@lecoffre.com", T0) is None

    def test_should_not_affect_another_email_when_one_account_fails(self, gateway: InMemoryLoginLockoutGateway):
        for _ in range(3):
            gateway.record_failed_login("alice@lecoffre.com", T0)

        assert gateway.is_locked("bob@lecoffre.com", T0) is None

    @pytest.mark.parametrize(
        "stored_email,queried_email",
        [
            ("Alice@Example.com", "alice@example.com"),
            ("  bob@example.com  ", "bob@example.com"),
            ("CAROL@EXAMPLE.COM", "carol@example.com"),
        ],
    )
    def test_should_treat_emails_as_same_when_only_case_or_whitespace_differs(
        self, gateway: InMemoryLoginLockoutGateway, stored_email: str, queried_email: str
    ):
        for _ in range(3):
            gateway.record_failed_login(stored_email, T0)

        assert gateway.is_locked(queried_email, T0) is not None

    def test_should_raise_value_error_when_max_failures_is_zero(self):
        with pytest.raises(ValueError, match="max_failures"):
            InMemoryLoginLockoutGateway(max_failures=0, lockout_seconds=60)

    def test_should_raise_value_error_when_lockout_seconds_is_zero(self):
        with pytest.raises(ValueError, match="lockout_seconds"):
            InMemoryLoginLockoutGateway(max_failures=3, lockout_seconds=0)
