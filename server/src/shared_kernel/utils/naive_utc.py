"""Bridge between naive DateTime columns and the aware datetimes the domain uses.

Every timestamp column in this schema is `sa.DateTime()`, which stores no offset,
while `TimeGateway` hands the domain aware UTC values. These two helpers are the
only sanctioned crossing point. Any repository persisting or comparing a datetime
must go through them.

**For secondary SQL adapters only.** Living under `utils/` makes these reachable
from anywhere, but they are meaningless outside the persistence boundary: the
domain and the application layer must only ever hold aware datetimes, and a
naive one reaching them is a bug rather than something to convert. If you find
yourself importing this outside a repository, the timestamp lost its timezone
further upstream and that is what needs fixing.
"""

from datetime import UTC, datetime
from typing import overload


def as_utc(value: datetime | None) -> datetime | None:
    """Re-attach UTC to a timestamp coming back from the database.

    The column type is naive, so a reloaded row yields naive datetimes while
    TimeGateway hands the domain aware ones. Comparing the two raises TypeError,
    which would blow up expiry checks on any row not still in the session's
    identity map. Everything written here is UTC, so re-attaching it is sound.
    """
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


@overload
def to_naive_utc(value: datetime) -> datetime: ...


@overload
def to_naive_utc(value: None) -> None: ...


def to_naive_utc(value: datetime | None) -> datetime | None:
    """Convert to UTC then drop the tzinfo, matching how the column stores it.

    Applied at every write and every comparison. Without it the driver decides
    what to do with an aware value, and SQLite keeps the local wall clock while
    discarding the offset: an instant of 11:00+02:00 lands as 11:00, two hours
    off. Expiry is then compared against a correctly normalised `now`, so an
    access would outlive its deadline by the size of the offset.
    """
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)
