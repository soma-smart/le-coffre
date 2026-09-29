"""Which paths skip the CSRF check, and which only look like they should."""

import pytest

from security.csrf_middleware import CsrfMiddleware


@pytest.mark.parametrize(
    "path",
    [
        "/api/extension/device",
        "/api/extension/device/exchange",
        "/api/one-time-links/consume",
    ],
)
def test_should_exempt_an_anonymous_route_and_its_children(path):
    assert CsrfMiddleware._is_exempt_route(path) is True


@pytest.mark.parametrize(
    "path",
    [
        # A sibling that merely shares the letters. A raw prefix match would
        # have exempted it, and with it any future cookie-authenticated route
        # somebody names this way.
        "/api/extension/devices",
        "/api/extension/device-admin/purge",
        "/api/one-time-links/consumed",
        # The cookie-authenticated half of pairing, mounted apart on purpose.
        "/api/extension/pairing/K7QM-3XR9/approve",
    ],
)
def test_should_not_exempt_a_route_that_only_shares_a_prefix(path):
    assert CsrfMiddleware._is_exempt_route(path) is False
