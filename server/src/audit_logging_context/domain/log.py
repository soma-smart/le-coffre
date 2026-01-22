from dataclasses import dataclass
from typing import TypeVar, Generic
from shared_kernel.pubsub import DomainEvent

T = TypeVar("T", bound=DomainEvent)


@dataclass
class Log(Generic[T]):
    event_type: str
    event: T
