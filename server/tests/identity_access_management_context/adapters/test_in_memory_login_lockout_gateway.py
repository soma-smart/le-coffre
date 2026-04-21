from unittest.mock import patch

import pytest
from identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway import (
    InMemoryLoginLockoutGateway,
)


@pytest.fixture
def lockout() -> InMemoryLoginLockoutGateway:
    return InMemoryLoginLockoutGateway(max_failures=3, lockout_seconds=60)


class TestInMemoryLoginLockoutGateway:
    def test_unknown_email_is_not_locked(self, lockout: InMemoryLoginLockoutGateway):
        retry_after = lockout.is_locked("alice@example.com")
        assert retry_after is None

    def test_init_rejects_zero_max_failures(self):
        with pytest.raises(ValueError, match="max_failures"):
            InMemoryLoginLockoutGateway(max_failures=0, lockout_seconds=60)

    def test_init_rejects_zero_lockout_seconds(self):
        with pytest.raises(ValueError, match="lockout_seconds"):
            InMemoryLoginLockoutGateway(max_failures=3, lockout_seconds=0)

    def test_init_rejects_negative_values(self):
        with pytest.raises(ValueError):
            InMemoryLoginLockoutGateway(max_failures=-1, lockout_seconds=60)
        with pytest.raises(ValueError):
            InMemoryLoginLockoutGateway(max_failures=3, lockout_seconds=-1)

    def test_record_failed_login_does_not_lock_below_threshold(self, lockout: InMemoryLoginLockoutGateway):
        for _ in range(2):
            lockout.record_failed_login("alice@example.com")
        retry_after = lockout.is_locked("alice@example.com")
        assert retry_after is None

    def test_record_failed_login_locks_when_threshold_reached(self, lockout: InMemoryLoginLockoutGateway):
        base_time = 1000.0
        with patch(
            "identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway.time.monotonic",
            return_value=base_time,
        ):
            for _ in range(3):
                lockout.record_failed_login("alice@example.com")
            retry_after = lockout.is_locked("alice@example.com")
        assert retry_after is not None
        assert retry_after == 60

    def test_retry_after_decreases_with_time(self, lockout: InMemoryLoginLockoutGateway):
        base_time = 1000.0
        with patch(
            "identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway.time.monotonic",
            return_value=base_time,
        ):
            for _ in range(3):
                lockout.record_failed_login("alice@example.com")

        with patch(
            "identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway.time.monotonic",
            return_value=base_time + 45,
        ):
            retry_after = lockout.is_locked("alice@example.com")
        assert retry_after is not None
        assert retry_after == 15  # 60 - 45 = 15 seconds remaining

    def test_is_unlocked_after_lockout_expires(self, lockout: InMemoryLoginLockoutGateway):
        base_time = 1000.0
        with patch(
            "identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway.time.monotonic",
            return_value=base_time,
        ):
            for _ in range(3):
                lockout.record_failed_login("alice@example.com")

        with patch(
            "identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway.time.monotonic",
            return_value=base_time + 61,
        ):
            retry_after = lockout.is_locked("alice@example.com")
        assert retry_after is None

    def test_counter_resets_after_lockout_applied(self, lockout: InMemoryLoginLockoutGateway):
        """After hitting the threshold, the counter returns to 0 so the NEXT
        lockout requires another full sequence of failures — not a single one."""
        base_time = 1000.0
        with patch(
            "identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway.time.monotonic",
            return_value=base_time,
        ):
            for _ in range(3):
                lockout.record_failed_login("alice@example.com")

        # Lockout expires, then one failure: should NOT re-lock
        with patch(
            "identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway.time.monotonic",
            return_value=base_time + 61,
        ):
            lockout.record_failed_login("alice@example.com")
            retry_after = lockout.is_locked("alice@example.com")
        assert retry_after is None

    def test_record_successful_login_clears_counter_and_lockout(self, lockout: InMemoryLoginLockoutGateway):
        for _ in range(2):
            lockout.record_failed_login("alice@example.com")
        lockout.record_successful_login("alice@example.com")
        # Next 2 failures must NOT lock (counter was reset)
        for _ in range(2):
            lockout.record_failed_login("alice@example.com")
        retry_after = lockout.is_locked("alice@example.com")
        assert retry_after is None

    def test_different_emails_are_independent(self, lockout: InMemoryLoginLockoutGateway):
        for _ in range(3):
            lockout.record_failed_login("alice@example.com")
        retry_after_bob = lockout.is_locked("bob@example.com")
        assert retry_after_bob is None

    @pytest.mark.parametrize(
        "a, b",
        [
            ("Alice@Example.com", "alice@example.com"),
            ("  bob@example.com  ", "bob@example.com"),
            ("CAROL@EXAMPLE.COM", "carol@example.com"),
        ],
    )
    def test_email_normalization_collapses_variants(self, lockout: InMemoryLoginLockoutGateway, a: str, b: str):
        for _ in range(3):
            lockout.record_failed_login(a)
        retry_after = lockout.is_locked(b)
        assert retry_after is not None

    def test_cleanup_evicts_stale_entries(self, lockout: InMemoryLoginLockoutGateway):
        base_time = 1000.0
        with patch(
            "identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway.time.monotonic",
            return_value=base_time,
        ):
            lockout.record_failed_login("old@example.com")

        with patch(
            "identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway.time.monotonic",
            return_value=base_time + 4000,
        ):
            lockout.record_failed_login("fresh@example.com")
            removed = lockout.cleanup(max_age_seconds=3600.0)

        assert removed == 1

    def test_cleanup_does_not_evict_locked_entries(self, lockout: InMemoryLoginLockoutGateway):
        """Even if the last activity is old, don't evict while the lockout is active —
        the entry is load-bearing until the lockout expires."""
        base_time = 1000.0
        with patch(
            "identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway.time.monotonic",
            return_value=base_time,
        ):
            for _ in range(3):
                lockout.record_failed_login("alice@example.com")

        with patch(
            "identity_access_management_context.adapters.secondary.in_memory_login_lockout_gateway.time.monotonic",
            return_value=base_time + 30,
        ):
            # max_age=10 would normally evict, but the lockout is still active (ends at base+60)
            removed = lockout.cleanup(max_age_seconds=10.0)

        assert removed == 0

    def test_record_successful_login_on_unknown_email_is_noop(self, lockout: InMemoryLoginLockoutGateway):
        # Must not raise
        lockout.record_successful_login("never-seen@example.com")
