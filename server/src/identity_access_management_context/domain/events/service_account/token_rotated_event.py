from dataclasses import dataclass

from ._event import ServiceAccountItemEvent


@dataclass(init=False)
class ServiceAccountTokenRotatedEvent(ServiceAccountItemEvent):
    """A service account's token was rotated."""
