from datetime import datetime
from typing import Protocol
from uuid import UUID

from identity_access_management_context.domain.entities import AuthSession


class AuthSessionRepository(Protocol):
    def create_session(self, user_id: UUID, refresh_token_jti: str, created_at: datetime) -> AuthSession: ...

    def get_active_by_user_id_and_refresh_jti(self, user_id: UUID, refresh_token_jti: str) -> AuthSession | None: ...

    def rotate_refresh_token_jti(
        self,
        session_id: UUID,
        expected_refresh_token_jti: str,
        new_refresh_token_jti: str,
        rotated_at: datetime,
    ) -> bool: ...

    def invalidate_by_user_id_and_refresh_jti(
        self, user_id: UUID, refresh_token_jti: str, invalidated_at: datetime
    ) -> None: ...

    def invalidate_all_for_user(self, user_id: UUID, invalidated_at: datetime) -> None: ...

    def purge_dead(self, cutoff: datetime) -> None: ...
