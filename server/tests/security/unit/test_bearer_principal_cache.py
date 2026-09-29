"""The cache that keeps a rate-limit guard from becoming an attack.

The middleware tests cover the hit path, since that is where it matters. What
they cannot cover is expiry: they run on a frozen clock, and the TTL is the
whole reason a revoked token cannot keep its bucket for long.
"""

from datetime import UTC, datetime, timedelta

from security.bearer_principal_cache import MAX_ENTRIES, BearerPrincipalCache

NOW = datetime(2026, 9, 17, 12, 0, 0, tzinfo=UTC)
USER = "22222222-2222-2222-2222-222222222222"


def test_should_report_nothing_when_the_token_was_never_seen():
    assert BearerPrincipalCache().get("unknown", NOW) is None


def test_should_return_the_user_when_the_token_was_seen_within_the_ttl():
    cache = BearerPrincipalCache(ttl_seconds=60)
    cache.put("hash", USER, NOW)

    assert cache.get("hash", NOW + timedelta(seconds=59)) == USER


def test_should_forget_the_token_once_the_ttl_has_passed():
    # What bounds the staleness. Revoking a credential cannot invalidate this
    # cache, so the only thing keeping a revoked token from holding its per-user
    # bucket indefinitely is that the entry dies on its own. Authorization is
    # never affected: get_current_principal queries on every request.
    cache = BearerPrincipalCache(ttl_seconds=60)
    cache.put("hash", USER, NOW)

    assert cache.get("hash", NOW + timedelta(seconds=60)) is None


def test_should_keep_the_newest_entry_when_evicting_a_full_cache():
    # Eviction drops everything rather than tracking usage. Losing an entry
    # costs one database lookup, so the cheap policy is the right one, but the
    # entry being written must survive it or a busy extension could evict
    # itself and never be cached at all.
    cache = BearerPrincipalCache()
    for index in range(MAX_ENTRIES):
        cache.put(f"hash-{index}", USER, NOW)

    cache.put("newest", "33333333-3333-3333-3333-333333333333", NOW)

    assert cache.get("newest", NOW) == "33333333-3333-3333-3333-333333333333"
