from dataclasses import dataclass


@dataclass(frozen=True)
class StoreEventResponse:
    """Response for store event operation. Empty as the operation returns void."""

    pass
