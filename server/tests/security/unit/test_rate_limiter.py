from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta

import pytest

from security.rate_limiter import InMemoryRateLimiter

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def limiter() -> InMemoryRateLimiter:
    return InMemoryRateLimiter()


def test_given_bucket_below_limit_when_checking_should_allow_request(limiter: InMemoryRateLimiter):
    result = limiter.check("ip:127.0.0.1:api", max_requests=5, window_seconds=60, now=T0)

    assert result.is_limited is False
    assert result.limit == 5
    assert result.remaining == 4
    assert result.retry_after == 0


def test_given_each_request_recorded_when_checking_should_decrement_remaining(limiter: InMemoryRateLimiter):
    for i in range(4):
        result = limiter.check("ip:127.0.0.1:api", max_requests=5, window_seconds=60, now=T0)
        assert result.remaining == 4 - i


def test_given_limit_reached_when_checking_should_block_request(limiter: InMemoryRateLimiter):
    for _ in range(5):
        limiter.check("ip:127.0.0.1:api", max_requests=5, window_seconds=60, now=T0)

    result = limiter.check("ip:127.0.0.1:api", max_requests=5, window_seconds=60, now=T0)

    assert result.is_limited is True
    assert result.remaining == 0


def test_given_bucket_limited_when_checking_should_report_retry_after_seconds(limiter: InMemoryRateLimiter):
    for _ in range(5):
        limiter.check("ip:127.0.0.1:api", max_requests=5, window_seconds=60, now=T0)

    result = limiter.check("ip:127.0.0.1:api", max_requests=5, window_seconds=60, now=T0 + timedelta(seconds=15))

    assert result.is_limited is True
    assert result.retry_after > 0


def test_given_different_keys_when_checking_should_isolate_buckets(limiter: InMemoryRateLimiter):
    for _ in range(5):
        limiter.check("ip:1.1.1.1:api", max_requests=5, window_seconds=60, now=T0)

    result = limiter.check("ip:2.2.2.2:api", max_requests=5, window_seconds=60, now=T0)

    assert result.is_limited is False
    assert result.remaining == 4


def test_given_window_elapsed_when_checking_should_release_capacity(limiter: InMemoryRateLimiter):
    for _ in range(5):
        limiter.check("ip:127.0.0.1:api", max_requests=5, window_seconds=60, now=T0)

    result = limiter.check("ip:127.0.0.1:api", max_requests=5, window_seconds=60, now=T0 + timedelta(seconds=61))

    assert result.is_limited is False
    assert result.remaining == 4


def test_given_requests_spanning_window_when_checking_should_apply_sliding_window(limiter: InMemoryRateLimiter):
    for _ in range(3):
        limiter.check("key", max_requests=5, window_seconds=60, now=T0)

    for _ in range(2):
        limiter.check("key", max_requests=5, window_seconds=60, now=T0 + timedelta(seconds=30))

    at_30 = limiter.check("key", max_requests=5, window_seconds=60, now=T0 + timedelta(seconds=30))
    assert at_30.is_limited is True

    at_61 = limiter.check("key", max_requests=5, window_seconds=60, now=T0 + timedelta(seconds=61))
    assert at_61.is_limited is False
    assert at_61.remaining == 2


def test_given_request_at_exact_window_boundary_when_checking_should_evict_oldest_timestamp(
    limiter: InMemoryRateLimiter,
):
    """The eviction condition uses `<=` (equality evicts) so a request at exactly
    `T0 + window_seconds` releases capacity. If a future refactor tightens to
    `<` (strict), every caller would experience a 1-second dead zone on every
    full bucket — subtle and hard to reproduce in manual testing. Pin the
    boundary behavior so the regression fails loudly here instead."""
    for _ in range(5):
        limiter.check("key", max_requests=5, window_seconds=60, now=T0)

    at_boundary = limiter.check("key", max_requests=5, window_seconds=60, now=T0 + timedelta(seconds=60))

    assert at_boundary.is_limited is False, (
        "A request at exactly T0 + window_seconds must evict the T0 timestamp; "
        "strict `<` in the eviction check would create a 1-second dead zone at the window edge"
    )
    assert at_boundary.remaining == 4


def test_given_concurrent_requests_when_checking_should_remain_correct(limiter: InMemoryRateLimiter):
    """Launch many requests in parallel; exactly max_requests must get through and the rest must be blocked."""

    def _check():
        return limiter.check("key", max_requests=3, window_seconds=60, now=T0)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_check) for _ in range(10)]
        results = [f.result() for f in as_completed(futures)]

    allowed = [r for r in results if not r.is_limited]
    limited = [r for r in results if r.is_limited]

    assert len(allowed) == 3
    assert len(limited) == 7
