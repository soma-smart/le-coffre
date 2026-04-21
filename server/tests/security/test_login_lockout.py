from unittest.mock import patch

import pytest
from security.login_lockout import InMemoryLoginLockout


@pytest.fixture
def lockout() -> InMemoryLoginLockout:
    return InMemoryLoginLockout(max_failures=3, lockout_seconds=60)


class TestInMemoryLoginLockout:
    def test_unknown_email_is_not_locked(self, lockout: InMemoryLoginLockout):
        locked, retry_after = lockout.is_locked("alice@example.com")
        assert locked is False
        assert retry_after == 0

    def test_init_rejects_zero_max_failures(self):
        with pytest.raises(ValueError, match="max_failures"):
            InMemoryLoginLockout(max_failures=0, lockout_seconds=60)

    def test_init_rejects_zero_lockout_seconds(self):
        with pytest.raises(ValueError, match="lockout_seconds"):
            InMemoryLoginLockout(max_failures=3, lockout_seconds=0)

    def test_init_rejects_negative_values(self):
        with pytest.raises(ValueError):
            InMemoryLoginLockout(max_failures=-1, lockout_seconds=60)
        with pytest.raises(ValueError):
            InMemoryLoginLockout(max_failures=3, lockout_seconds=-1)

    def test_record_failure_does_not_lock_below_threshold(self, lockout: InMemoryLoginLockout):
        for _ in range(2):
            lockout.record_failure("alice@example.com")
        locked, retry_after = lockout.is_locked("alice@example.com")
        assert locked is False
        assert retry_after == 0

    def test_record_failure_locks_when_threshold_reached(self, lockout: InMemoryLoginLockout):
        base_time = 1000.0
        with patch("security.login_lockout.time.monotonic", return_value=base_time):
            for _ in range(3):
                lockout.record_failure("alice@example.com")
            locked, retry_after = lockout.is_locked("alice@example.com")
        assert locked is True
        assert retry_after == 60

    def test_retry_after_decreases_with_time(self, lockout: InMemoryLoginLockout):
        base_time = 1000.0
        with patch("security.login_lockout.time.monotonic", return_value=base_time):
            for _ in range(3):
                lockout.record_failure("alice@example.com")

        with patch("security.login_lockout.time.monotonic", return_value=base_time + 45):
            locked, retry_after = lockout.is_locked("alice@example.com")
        assert locked is True
        assert retry_after == 15  # 60 - 45 = 15 seconds remaining

    def test_is_unlocked_after_lockout_expires(self, lockout: InMemoryLoginLockout):
        base_time = 1000.0
        with patch("security.login_lockout.time.monotonic", return_value=base_time):
            for _ in range(3):
                lockout.record_failure("alice@example.com")

        with patch("security.login_lockout.time.monotonic", return_value=base_time + 61):
            locked, retry_after = lockout.is_locked("alice@example.com")
        assert locked is False
        assert retry_after == 0

    def test_counter_resets_after_lockout_applied(self, lockout: InMemoryLoginLockout):
        """After hitting the threshold, the counter returns to 0 so the NEXT
        lockout requires another full sequence of failures — not a single one."""
        base_time = 1000.0
        with patch("security.login_lockout.time.monotonic", return_value=base_time):
            for _ in range(3):
                lockout.record_failure("alice@example.com")

        # Lockout expires, then one failure: should NOT re-lock
        with patch("security.login_lockout.time.monotonic", return_value=base_time + 61):
            lockout.record_failure("alice@example.com")
            locked, _ = lockout.is_locked("alice@example.com")
        assert locked is False

    def test_record_success_clears_counter_and_lockout(self, lockout: InMemoryLoginLockout):
        for _ in range(2):
            lockout.record_failure("alice@example.com")
        lockout.record_success("alice@example.com")
        # Next 2 failures must NOT lock (counter was reset)
        for _ in range(2):
            lockout.record_failure("alice@example.com")
        locked, _ = lockout.is_locked("alice@example.com")
        assert locked is False

    def test_different_emails_are_independent(self, lockout: InMemoryLoginLockout):
        for _ in range(3):
            lockout.record_failure("alice@example.com")
        locked_bob, _ = lockout.is_locked("bob@example.com")
        assert locked_bob is False

    @pytest.mark.parametrize(
        "a, b",
        [
            ("Alice@Example.com", "alice@example.com"),
            ("  bob@example.com  ", "bob@example.com"),
            ("CAROL@EXAMPLE.COM", "carol@example.com"),
        ],
    )
    def test_email_normalization_collapses_variants(self, lockout: InMemoryLoginLockout, a: str, b: str):
        for _ in range(3):
            lockout.record_failure(a)
        locked, _ = lockout.is_locked(b)
        assert locked is True

    def test_cleanup_evicts_stale_entries(self, lockout: InMemoryLoginLockout):
        base_time = 1000.0
        with patch("security.login_lockout.time.monotonic", return_value=base_time):
            lockout.record_failure("old@example.com")

        with patch("security.login_lockout.time.monotonic", return_value=base_time + 4000):
            lockout.record_failure("fresh@example.com")
            removed = lockout.cleanup(max_age_seconds=3600.0)

        assert removed == 1

    def test_cleanup_does_not_evict_locked_entries(self, lockout: InMemoryLoginLockout):
        """Even if the last activity is old, don't evict while the lockout is active —
        the entry is load-bearing until the lockout expires."""
        base_time = 1000.0
        with patch("security.login_lockout.time.monotonic", return_value=base_time):
            for _ in range(3):
                lockout.record_failure("alice@example.com")

        with patch("security.login_lockout.time.monotonic", return_value=base_time + 30):
            # max_age=10 would normally evict, but the lockout is still active (ends at base+60)
            removed = lockout.cleanup(max_age_seconds=10.0)

        assert removed == 0

    def test_record_success_on_unknown_email_is_noop(self, lockout: InMemoryLoginLockout):
        # Must not raise
        lockout.record_success("never-seen@example.com")
