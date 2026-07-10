import ipaddress
import socket
from urllib.parse import ParseResult, urlparse

from identity_access_management_context.domain.exceptions import (
    DisallowedSsoEndpointException,
)

_DEFAULT_PORT_BY_SCHEME = {"https": 443, "http": 80}


class SsoUrlValidator:
    """Guards SSO endpoint URLs against SSRF.

    Forces https and rejects any URL whose hostname resolves to a
    private, loopback, link-local, reserved, multicast or unspecified
    address (covers cloud metadata endpoints such as 169.254.169.254).

    When ``allow_private_networks`` is True the guard is relaxed to permit
    http and internal addresses, which is required only for local
    development and the localhost-bound OIDC mock used in tests.
    """

    def __init__(self, allow_private_networks: bool = False) -> None:
        self._allow_private_networks = allow_private_networks

    def validate_scheme(self, url: str) -> None:
        """Reject non-http(s) schemes (``javascript:``, ``data:``, …) and empty hosts.

        Cheap, no DNS resolution. Use where the URL is handed to a *client* to
        navigate to (the server never connects there), so only the scheme matters —
        e.g. an authorization endpoint returned by ``/auth/sso/url``. This closes the
        stored-XSS vector (``window.location`` on a ``javascript:`` URL).
        """
        self._require_http_scheme(url)

    def validate(self, url: str) -> None:
        parsed = self._require_http_scheme(url)
        scheme = parsed.scheme.lower()

        if self._allow_private_networks:
            return

        port = parsed.port or _DEFAULT_PORT_BY_SCHEME[scheme]
        try:
            resolved = socket.getaddrinfo(parsed.hostname, port, proto=socket.IPPROTO_TCP)
        except socket.gaierror as error:
            raise DisallowedSsoEndpointException() from error

        for *_, sockaddr in resolved:
            ip = ipaddress.ip_address(sockaddr[0])
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
                or ip.is_unspecified
            ):
                raise DisallowedSsoEndpointException()

    def _require_http_scheme(self, url: str) -> ParseResult:
        parsed = urlparse((url or "").strip())
        allowed_schemes = {"https", "http"} if self._allow_private_networks else {"https"}
        if parsed.scheme.lower() not in allowed_schemes or not parsed.hostname:
            raise DisallowedSsoEndpointException()
        return parsed
