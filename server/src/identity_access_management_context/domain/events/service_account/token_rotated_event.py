from dataclasses import dataclass

from ._event import ServiceAccountEvent


@dataclass(init=False)
class ServiceAccountTokenRotatedEvent(ServiceAccountEvent):
    """A service account's token was rotated."""
