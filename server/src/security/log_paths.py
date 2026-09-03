"""Request paths, made safe to log."""

import re

# The vocabulary of this API's static route segments: lowercase words with
# hyphens, none longer than this. `register-admin`, `one-time-links` and
# `csrf-token` all fit; a UUID, a pairing code or any opaque value does not.
_STATIC_SEGMENT = re.compile(r"^[a-z][a-z0-9-]{0,23}$")

_REDACTED = "*"


def sanitize_path_for_log(path: str) -> str:
    """Replace every path segment that is not static route vocabulary.

    Truncating by segment count does not work, which is how the previous
    version leaked what it promised to hide: an identifier sits at whatever
    depth its route puts it, so any fixed cut is wrong somewhere. Keeping three
    segments of ``/api/passwords/<uuid>`` keeps the uuid, while keeping fewer
    would reduce ``/api/extension/pairing/<code>/approve`` to a prefix that no
    longer says which operation was called.

    Redacting by shape sidesteps the depth question: the route stays
    recognisable and the values do not survive. Deliberately conservative,
    anything that is not plainly a route word is replaced, so a segment this
    module has never seen is dropped rather than logged.

    Middleware runs before routing, so the matched route template is not
    available here; this is the best a raw path allows.
    """
    segments = [segment for segment in path.split("/") if segment]
    kept = [segment if _STATIC_SEGMENT.fullmatch(segment) else _REDACTED for segment in segments]
    return "/" + "/".join(kept)
