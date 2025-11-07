from typing import Protocol
from datetime import datetime


class TimeProvider(Protocol):
    def get_current_time(self) -> datetime:
        """Returns the current datetime in UTC"""
        ...
