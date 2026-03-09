from datetime import UTC, datetime

from shared_kernel.application.gateways import TimeGateway


class UtcTimeGateway(TimeGateway):
    def get_current_time(self) -> datetime:
        """Returns the current datetime in UTC"""
        return datetime.now(UTC)
