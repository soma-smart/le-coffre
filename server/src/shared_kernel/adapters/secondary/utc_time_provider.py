from datetime import datetime, UTC


class UtcTimeProvider:
    def get_current_time(self) -> datetime:
        """Returns the current datetime in UTC"""
        return datetime.now(UTC)
