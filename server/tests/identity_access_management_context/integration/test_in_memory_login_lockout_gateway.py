from unittest.mock import patch

import pytest
from identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway import (
    InMemoryLoginLockoutGateway,
)

MONOTONIC_PATCH_PATH = (
    "identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway.time.monotonic"
)


@pytest.fixture
def gateway() -> InMemoryLoginLockoutGateway:
    return InMemoryLoginLockoutGateway(max_failures=3, lockout_seconds=60)


class TestInMemoryLoginLockoutGateway:
    def test_should_return_none_when_email_has_no_recorded_failures(self, gateway: InMemoryLoginLockoutGateway):
        assert gateway.is_locked("unknown@lecoffre.com") is None

    def test_should_not_lock_when_failures_are_below_threshold(self, gateway: InMemoryLoginLockoutGateway):
        for _ in range(2):
            gateway.record_failed_login("alice@lecoffre.com")

        assert gateway.is_locked("alice@lecoffre.com") is None

    def test_should_lock_when_failure_count_reaches_threshold(self, gateway: InMemoryLoginLockoutGateway):
        with patch(MONOTONIC_PATCH_PATH, return_value=1000.0):
            for _ in range(3):
                gateway.record_failed_login("alice@lecoffre.com")
            assert gateway.is_locked("alice@lecoffre.com") == 60

    def test_should_return_remaining_seconds_when_account_currently_locked(self, gateway: InMemoryLoginLockoutGateway):
        with patch(MONOTONIC_PATCH_PATH, return_value=1000.0):
            for _ in range(3):
                gateway.record_failed_login("alice@lecoffre.com")

        with patch(MONOTONIC_PATCH_PATH, return_value=1045.0):
            assert gateway.is_locked("alice@lecoffre.com") == 15

    def test_should_return_none_when_lockout_duration_has_elapsed(self, gateway: InMemoryLoginLockoutGateway):
        with patch(MONOTONIC_PATCH_PATH, return_value=1000.0):
            for _ in range(3):
                gateway.record_failed_login("alice@lecoffre.com")

        with patch(MONOTONIC_PATCH_PATH, return_value=1061.0):
            assert gateway.is_locked("alice@lecoffre.com") is None

    def test_should_require_fresh_sequence_when_recording_failure_after_expired_lockout(
        self, gateway: InMemoryLoginLockoutGateway
    ):
        with patch(MONOTONIC_PATCH_PATH, return_value=1000.0):
            for _ in range(3):
                gateway.record_failed_login("alice@lecoffre.com")

        with patch(MONOTONIC_PATCH_PATH, return_value=1061.0):
            gateway.record_failed_login("alice@lecoffre.com")
            assert gateway.is_locked("alice@lecoffre.com") is None

    def test_should_clear_failure_state_when_successful_login_is_recorded(self, gateway: InMemoryLoginLockoutGateway):
        for _ in range(2):
            gateway.record_failed_login("alice@lecoffre.com")

        gateway.record_successful_login("alice@lecoffre.com")

        for _ in range(2):
            gateway.record_failed_login("alice@lecoffre.com")

        assert gateway.is_locked("alice@lecoffre.com") is None

    def test_should_not_affect_another_email_when_one_account_fails(self, gateway: InMemoryLoginLockoutGateway):
        for _ in range(3):
            gateway.record_failed_login("alice@lecoffre.com")

        assert gateway.is_locked("bob@lecoffre.com") is None

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
            gateway.record_failed_login(stored_email)

        assert gateway.is_locked(queried_email) is not None

    def test_should_raise_value_error_when_max_failures_is_zero(self):
        with pytest.raises(ValueError, match="max_failures"):
            InMemoryLoginLockoutGateway(max_failures=0, lockout_seconds=60)

    def test_should_raise_value_error_when_lockout_seconds_is_zero(self):
        with pytest.raises(ValueError, match="lockout_seconds"):
            InMemoryLoginLockoutGateway(max_failures=3, lockout_seconds=0)
