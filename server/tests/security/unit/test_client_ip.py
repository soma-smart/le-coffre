from types import SimpleNamespace

import pytest

from security import client_ip as client_ip_module
from security.client_ip import resolve_client_ip


@pytest.fixture(autouse=True)
def _reset_missing_peer_latch():
    """The module-level latch that suppresses repeated "missing peer" warnings
    persists across tests in the same process; reset it per-test so tests that
    assert on the WARNING can run independently of ordering."""
    client_ip_module._missing_peer_warned = False
    yield
    client_ip_module._missing_peer_warned = False


def _request(peer: str | None, xff: str | None = None):
    """Minimal Request-shaped stub — resolve_client_ip only reads .client.host and .headers."""
    headers = {}
    if xff is not None:
        headers["X-Forwarded-For"] = xff
    client = SimpleNamespace(host=peer) if peer is not None else None
    return SimpleNamespace(client=client, headers=headers)


def test_given_no_xff_header_when_resolving_should_return_peer_host():
    request = _request(peer="10.0.0.5")

    assert resolve_client_ip(request, trusted_proxies={"127.0.0.1"}, hops=1) == "10.0.0.5"


def test_given_no_client_and_no_xff_when_resolving_should_return_unknown_and_log_warning(
    caplog: pytest.LogCaptureFixture,
):
    """When the TCP peer cannot be determined every such request keys on the
    same `unknown` bucket. That's a small blast radius on its own, but the
    condition must surface at WARNING so an operator can spot a misconfigured
    proxy — silent fallback hides the signal entirely."""
    request = _request(peer=None)

    with caplog.at_level("WARNING", logger="security.client_ip"):
        assert resolve_client_ip(request, trusted_proxies={"127.0.0.1"}, hops=1) == "unknown"

    warnings = [rec for rec in caplog.records if rec.levelname == "WARNING"]
    assert warnings, "Missing TCP peer must log a WARNING so misconfigured proxies are visible to SRE"
    msg = warnings[0].getMessage().lower()
    assert "unknown" in msg or "peer" in msg


def test_given_repeated_missing_peer_when_resolving_should_log_warning_only_once(
    caplog: pytest.LogCaptureFixture,
):
    """A misconfigured reverse proxy could produce thousands of peer-less
    requests per minute; the WARNING must be latched per process so SRE sees
    the signal once without log-flood. Subsequent peer-less requests still get
    the 'unknown' bucket, so the rate-limit 429 continues to cap volume."""
    request = _request(peer=None)

    with caplog.at_level("WARNING", logger="security.client_ip"):
        for _ in range(100):
            assert resolve_client_ip(request, trusted_proxies={"127.0.0.1"}, hops=1) == "unknown"

    warnings = [rec for rec in caplog.records if rec.levelname == "WARNING"]
    assert len(warnings) == 1, f"Expected one latched WARNING, got {len(warnings)}"


def test_given_untrusted_peer_when_resolving_should_ignore_xff_header():
    request = _request(peer="203.0.113.7", xff="1.2.3.4, 5.6.7.8")

    assert resolve_client_ip(request, trusted_proxies={"127.0.0.1"}, hops=1) == "203.0.113.7"


def test_given_one_trusted_hop_when_resolving_should_use_rightmost_xff_entry():
    request = _request(peer="127.0.0.1", xff="203.0.113.1, 10.0.0.5")

    assert resolve_client_ip(request, trusted_proxies={"127.0.0.1"}, hops=1) == "10.0.0.5"


def test_given_n_trusted_hops_when_resolving_should_use_nth_from_right_xff_entry():
    request = _request(peer="127.0.0.1", xff="203.0.113.1, 10.0.0.5, 192.168.0.1")

    assert resolve_client_ip(request, trusted_proxies={"127.0.0.1"}, hops=2) == "10.0.0.5"


def test_given_xff_shorter_than_hops_when_resolving_should_fall_back_to_peer():
    request = _request(peer="127.0.0.1", xff="10.0.0.5")

    assert resolve_client_ip(request, trusted_proxies={"127.0.0.1"}, hops=3) == "127.0.0.1"


def test_given_empty_xff_header_when_resolving_should_return_peer():
    request = _request(peer="127.0.0.1", xff="")

    assert resolve_client_ip(request, trusted_proxies={"127.0.0.1"}, hops=1) == "127.0.0.1"


@pytest.mark.parametrize("hops", [0, -1])
def test_given_non_positive_hops_when_resolving_should_return_peer(hops: int):
    request = _request(peer="127.0.0.1", xff="10.0.0.5")

    assert resolve_client_ip(request, trusted_proxies={"127.0.0.1"}, hops=hops) == "127.0.0.1"
