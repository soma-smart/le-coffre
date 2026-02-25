from unittest.mock import patch

import pytest

from security.rate_limiter import InMemoryRateLimiter


@pytest.fixture
def limiter() -> InMemoryRateLimiter:
    return InMemoryRateLimiter()


class TestInMemoryRateLimiter:
    def test_should_allow_requests_under_limit(self, limiter: InMemoryRateLimiter):
        result = limiter.check("ip:127.0.0.1:api", max_requests=5, window_seconds=60)

        assert result.is_limited is False
        assert result.limit == 5
        assert result.remaining == 4
        assert result.retry_after == 0

    def test_should_decrement_remaining_on_each_request(
        self, limiter: InMemoryRateLimiter
    ):
        for i in range(4):
            result = limiter.check(
                "ip:127.0.0.1:api", max_requests=5, window_seconds=60
            )
            assert result.remaining == 4 - i

    def test_should_block_requests_when_limit_reached(
        self, limiter: InMemoryRateLimiter
    ):
        for _ in range(5):
            limiter.check("ip:127.0.0.1:api", max_requests=5, window_seconds=60)

        result = limiter.check("ip:127.0.0.1:api", max_requests=5, window_seconds=60)

        assert result.is_limited is True
        assert result.remaining == 0
        assert result.retry_after > 0

    def test_should_track_separate_keys_independently(
        self, limiter: InMemoryRateLimiter
    ):
        for _ in range(5):
            limiter.check("ip:1.1.1.1:api", max_requests=5, window_seconds=60)

        result = limiter.check("ip:2.2.2.2:api", max_requests=5, window_seconds=60)

        assert result.is_limited is False
        assert result.remaining == 4

    def test_should_reset_after_window_expires(self, limiter: InMemoryRateLimiter):
        base_time = 1000.0

        with patch("security.rate_limiter.time.monotonic", return_value=base_time):
            for _ in range(5):
                limiter.check("ip:127.0.0.1:api", max_requests=5, window_seconds=60)

        with patch("security.rate_limiter.time.monotonic", return_value=base_time + 61):
            result = limiter.check(
                "ip:127.0.0.1:api", max_requests=5, window_seconds=60
            )

        assert result.is_limited is False
        assert result.remaining == 4

    def test_should_use_sliding_window(self, limiter: InMemoryRateLimiter):
        base_time = 1000.0

        # Make 3 requests at t=0
        with patch("security.rate_limiter.time.monotonic", return_value=base_time):
            for _ in range(3):
                limiter.check("key", max_requests=5, window_seconds=60)

        # Make 2 requests at t=30 (still within window)
        with patch("security.rate_limiter.time.monotonic", return_value=base_time + 30):
            for _ in range(2):
                limiter.check("key", max_requests=5, window_seconds=60)

        # At t=30, we've used 5 requests => should be blocked
        with patch("security.rate_limiter.time.monotonic", return_value=base_time + 30):
            result = limiter.check("key", max_requests=5, window_seconds=60)
            assert result.is_limited is True

        # At t=61, the first 3 requests expired => 2 remain, should allow
        with patch("security.rate_limiter.time.monotonic", return_value=base_time + 61):
            result = limiter.check("key", max_requests=5, window_seconds=60)
            assert result.is_limited is False
            assert result.remaining == 2

    def test_should_cleanup_expired_entries(self, limiter: InMemoryRateLimiter):
        base_time = 1000.0

        with patch("security.rate_limiter.time.monotonic", return_value=base_time):
            limiter.check("old_key", max_requests=10, window_seconds=60)

        with patch(
            "security.rate_limiter.time.monotonic", return_value=base_time + 400
        ):
            limiter.check("fresh_key", max_requests=10, window_seconds=60)
            removed = limiter.cleanup(max_age_seconds=300)

        assert removed == 1

    def test_should_reset_all_state(self, limiter: InMemoryRateLimiter):
        for _ in range(5):
            limiter.check("key", max_requests=5, window_seconds=60)

        limiter.reset()

        result = limiter.check("key", max_requests=5, window_seconds=60)
        assert result.is_limited is False
        assert result.remaining == 4
