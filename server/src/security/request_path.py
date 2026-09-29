"""The request path as the security middlewares must see it."""

from fastapi import Request


def api_path(request: Request) -> str:
    """Return the path with the application's root path prefix guaranteed.

    The application is mounted with ``root_path="/api"``, and Starlette's router
    strips that prefix only when it is present: ``/passwords`` and
    ``/api/passwords`` both reach the same handler. Every middleware that keys
    on the path, from the rate limiter to the bearer read-only guard, matches
    against ``/api/...``, so a request that arrives without the prefix used to
    slip past all of them while still being routed. Behind nginx that cannot
    happen, since only ``/api/`` is proxied, but the backend port is published
    for debugging in development and nothing there stops it.

    Normalising once, here, is the least invasive fix: the middlewares keep
    their ``/api``-prefixed tables and the router keeps its behaviour. Without a
    configured root path the path is returned as is, which is what the unit
    tests that declare their routes in full rely on.
    """
    root_path = request.scope.get("root_path") or ""
    path = request.url.path
    if root_path and path != root_path and not path.startswith(root_path + "/"):
        return root_path + path
    return path
