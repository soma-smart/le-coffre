from typing import Protocol


class EventRepository(Protocol):
    def append_event(self, event): ...
