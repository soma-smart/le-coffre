from types import SimpleNamespace

import pytest
from shared_kernel.adapters.primary.client_ip import resolve_client_ip


def _request(peer: str | None, xff: str | None = None):
    """Minimal Request-shaped stub — only .client.host and headers are read."""
    headers = {}
    if xff is not None:
        headers["X-Forwarded-For"] = xff
    client = SimpleNamespace(host=peer) if peer is not None else None
    return SimpleNamespace(client=client, headers=headers)


class TestResolveClientIp:
    def test_returns_peer_host_when_no_xff(self):
        req = _request(peer="10.0.0.5")
        assert resolve_client_ip(req, trusted_proxies={"127.0.0.1"}, hops=1) == "10.0.0.5"

    def test_returns_unknown_when_no_client_and_no_xff(self):
        req = _request(peer=None)
        assert resolve_client_ip(req, trusted_proxies={"127.0.0.1"}, hops=1) == "unknown"

    def test_ignores_xff_when_peer_is_not_trusted(self):
        req = _request(peer="203.0.113.7", xff="1.2.3.4, 5.6.7.8")
        assert resolve_client_ip(req, trusted_proxies={"127.0.0.1"}, hops=1) == "203.0.113.7"

    def test_uses_rightmost_xff_entry_when_hops_is_one(self):
        req = _request(peer="127.0.0.1", xff="203.0.113.1, 10.0.0.5")
        assert resolve_client_ip(req, trusted_proxies={"127.0.0.1"}, hops=1) == "10.0.0.5"

    def test_uses_second_from_right_when_hops_is_two(self):
        req = _request(peer="127.0.0.1", xff="203.0.113.1, 10.0.0.5, 192.168.0.1")
        assert resolve_client_ip(req, trusted_proxies={"127.0.0.1"}, hops=2) == "10.0.0.5"

    def test_falls_back_to_peer_when_xff_is_shorter_than_hops(self):
        req = _request(peer="127.0.0.1", xff="10.0.0.5")
        assert resolve_client_ip(req, trusted_proxies={"127.0.0.1"}, hops=3) == "127.0.0.1"

    def test_strips_whitespace_in_xff_entries(self):
        req = _request(peer="127.0.0.1", xff="  203.0.113.1  ,  10.0.0.5  ")
        assert resolve_client_ip(req, trusted_proxies={"127.0.0.1"}, hops=1) == "10.0.0.5"

    def test_ignores_empty_xff(self):
        req = _request(peer="127.0.0.1", xff="")
        assert resolve_client_ip(req, trusted_proxies={"127.0.0.1"}, hops=1) == "127.0.0.1"

    def test_ipv6_loopback_trusted_by_default_callers(self):
        req = _request(peer="::1", xff="10.0.0.5")
        assert resolve_client_ip(req, trusted_proxies={"127.0.0.1", "::1"}, hops=1) == "10.0.0.5"

    @pytest.mark.parametrize("hops", [0, -1])
    def test_non_positive_hops_returns_peer(self, hops):
        req = _request(peer="127.0.0.1", xff="10.0.0.5")
        assert resolve_client_ip(req, trusted_proxies={"127.0.0.1"}, hops=hops) == "127.0.0.1"
