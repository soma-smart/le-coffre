from uuid import UUID, uuid4
from datetime import timedelta

from shared_kernel.time import TimeProvider


class AuthenticationSession:
    def __init__(
        self,
        user_id: UUID,
        jwt_token: str,
        time_provider: TimeProvider,
        ttl_hours: int = 24,
    ):
        self.id = uuid4()
        self.user_id = user_id
        self.jwt_token = jwt_token
        self._time_provider = time_provider
        self.created_at = self._time_provider.get_current_time()
        self.expires_at = self.created_at + timedelta(hours=ttl_hours)

    def is_expired(self) -> bool:
        return self._time_provider.get_current_time() >= self.expires_at
