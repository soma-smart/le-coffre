from datetime import datetime
from typing import Protocol


class TimeGateway(Protocol):
    def get_current_time(self) -> datetime:
        """Returns the current datetime in UTC"""
        ...
