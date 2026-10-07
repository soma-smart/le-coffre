"""Routes that carry secret material must stay out of the OTel spans.

Checked without OpenTelemetry installed: the instrumentation matches each
excluded entry against the request URL with re.search, which is replayed here
on the app's real routes, so a route added later under a covered prefix is
checked too.
"""

import re

import pytest

from main import app
from monitoring import _EXCLUDED_URLS

_SECRET_ROUTE_PREFIXES = (
    # Hands out sealed shares and takes the key that closes their link
    "/vault/share-links",
)


def _is_excluded(path: str) -> bool:
    url = f"http://testserver/api{path}"
    return any(re.search(pattern, url) for pattern in _EXCLUDED_URLS.split(","))


def _routes_under(prefix: str) -> list[str]:
    # The routers are included nested, so app.routes does not list their paths;
    # the OpenAPI schema does, without the /api root path.
    return sorted(path for path in app.openapi()["paths"] if path.startswith(prefix))


@pytest.mark.parametrize("prefix", _SECRET_ROUTE_PREFIXES)
def test_every_share_link_route_is_kept_out_of_traces(prefix):
    routes = _routes_under(prefix)

    assert routes, f"no route under {prefix}: the check would pass vacuously"
    assert [path for path in routes if not _is_excluded(path)] == []
