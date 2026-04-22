from datetime import UTC, datetime


class FakeTimeGateway:
    """Controllable clock for tests that need to observe time-dependent behavior."""

    def __init__(self, fixed_time: datetime | None = None):
        self._fixed_time = fixed_time or datetime.now(UTC)

    def get_current_time(self) -> datetime:
        return self._fixed_time

    def set_current_time(self, time: datetime) -> None:
        self._fixed_time = time
