from datetime import datetime

from shared_kernel.application.gateways import TimeGateway


class FakeTimeGateway(TimeGateway):
    """Fake time gateway for testing that allows setting the current time."""

    def __init__(self, current_time: datetime | None = None):
        self._current_time = current_time or datetime.now()

    def get_current_time(self) -> datetime:
        return self._current_time

    def set_current_time(self, time: datetime) -> None:
        """Set the current time (for testing purposes)."""
        self._current_time = time
