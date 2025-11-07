from datetime import datetime, UTC


class FakeTimeProvider:
    def __init__(self, fixed_time: datetime | None = None):
        self._fixed_time = fixed_time or datetime.now(UTC)

    def get_current_time(self) -> datetime:
        """Returns the fixed datetime"""
        return self._fixed_time

    def set_current_time(self, time: datetime) -> None:
        """Sets the fixed time to return"""
        self._fixed_time = time
